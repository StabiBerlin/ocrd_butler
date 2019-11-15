# -*- coding: utf-8 -*-

"""Testing the processor configuration for `ocrd_butler` package."""

import pytest
import requests

from flask_testing import TestCase

from ocrd_calamari.recognize import CalamariRecognize
from ocrd_tesserocr.recognize import TesserocrRecognize
from ocrd_tesserocr.segment_region import TesserocrSegmentRegion

from ocrd_butler.factory import create_app
from ocrd_butler.api.processors import PROCESSORS_CONFIG
from ocrd_butler.api.processors import PROCESSORS_ACTION
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

    def test_tesserocr_integration(self):
        """Check if ocr_tesserocr is importable."""
        assert "TesserocrRecognize" in PROCESSORS_CONFIG
        assert "TesserocrRecognize" in PROCESSOR_NAMES
        assert PROCESSORS_CONFIG["TesserocrRecognize"]["class"] == TesserocrRecognize
        assert "TesserocrSegmentRegion" in PROCESSORS_CONFIG
        assert PROCESSORS_CONFIG["TesserocrSegmentRegion"]["class"] == TesserocrSegmentRegion
        assert "TesserocrSegmentLine" in PROCESSORS_CONFIG
        assert "TesserocrSegmentWord" in PROCESSORS_CONFIG
        assert "TesserocrCrop" in PROCESSORS_CONFIG
        assert "TesserocrDeskew" in PROCESSORS_CONFIG
        assert "TesserocrBinarize" in PROCESSORS_CONFIG

    def test_tesserocr_information(self):
        """Check if tesserocr processor is visible."""
        response = self.client.get("/processors")
        self.assert200(response)
        self.assert_template_used("processors.html")
        assert b'TesserocrDeskew' in response.data

    def test_tesserocr_parameters(self):
        """Check if ocr_tesserocr is importable."""
        parameters = PROCESSORS_ACTION["TesserocrRecognize"]["parameters"]
        assert "textequiv_level" in parameters
        assert parameters["textequiv_level"] == "line"
        assert parameters["overwrite_words"] == False
        assert "model" not in parameters

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
