# -*- coding: utf-8 -*-

"""Testing the processor api for `ocrd_butler` package."""

from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app

from . import requires_ocrd_all


class ApiTests(TestCase):
    """Test our api."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def create_app(self):
        return create_app(config=TestingConfig)

    @requires_ocrd_all
    def test_get_processors(self):
        """Check if our processors are getable."""
        response = self.client.get("/api/processors")
        assert response.status_code == 200
        assert len(response.json) == len(TestingConfig.PROCESSORS)
        for i, processor in enumerate(response.json):
            assert processor["executable"] == TestingConfig.PROCESSORS[i]
