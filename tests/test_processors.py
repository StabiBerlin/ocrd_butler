# -*- coding: utf-8 -*-

"""Testing the processor configuration for `ocrd_butler` package."""

import pytest
import requests

from flask_testing import TestCase

from ocrd_calamari.recognize import CalamariRecognize

from ocrd_butler.factory import create_app
from ocrd_butler.api.processors import PROCESSORS_CONFIG
from ocrd_butler.api.processors import PROCESSOR_NAMES
# from ocrd_butler.api.processors import PROCESSORS
from ocrd_butler.config import TestingConfig


class ProcessorsTests(TestCase):
    """Test our predefined processors."""

    def create_app(self):
        return create_app(config=TestingConfig)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_calamari_integration(self):
        """Check if ocr_calamari is importable."""
        assert "CalamariRecognize" in PROCESSORS_CONFIG
        assert "CalamariRecognize" in PROCESSOR_NAMES
        assert PROCESSORS_CONFIG["CalamariRecognize"]["class"] == CalamariRecognize

    def test_calamari_information(self):
        """Check if calamari processor is visible."""
        response = self.client.get("/processors")
        self.assert200(response)
        self.assert_template_used("processors.html")
        assert b'CalamariRecognize' in response.data
