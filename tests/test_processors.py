# -*- coding: utf-8 -*-

"""Testing the processor configuration for `ocrd_butler` package."""

from flask_testing import TestCase

from ocrd_butler.factory import create_app
from ocrd_butler.api.processors import PROCESSORS_CONFIG
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.api.processors import PROCESSOR_NAMES
from ocrd_butler.config import TestingConfig


class ProcessorsTests(TestCase):
    """Test our predefined processors."""

    def create_app(self):
        return create_app(config=TestingConfig)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_processor_names(self):
        """ Test our chain definition. """
        assert "ocrd-olena-binarize" in PROCESSOR_NAMES
        assert "ocrd-tesserocr-recognize" in PROCESSOR_NAMES
        assert "ocrd-dinglehopper" in PROCESSOR_NAMES
        assert "ocrd-calamari-recognize" in PROCESSOR_NAMES
        assert "ocrd-segment-repair" in PROCESSOR_NAMES
        assert "ocrd-keraslm-rate" in PROCESSOR_NAMES
        assert "ocrd-anybaseocr-binarize" in PROCESSOR_NAMES

    def test_tesserocr_integration(self):
        """Check if ocr_tesserocr is importable."""
        assert "ocrd-tesserocr-recognize" in PROCESSORS_CONFIG
        assert PROCESSORS_CONFIG["ocrd-tesserocr-recognize"]["executable"] ==\
            "ocrd-tesserocr-recognize"
        assert "ocrd-tesserocr-segment-region" in PROCESSORS_CONFIG
        assert PROCESSORS_CONFIG["ocrd-tesserocr-segment-region"]["executable"] ==\
            "ocrd-tesserocr-segment-region"
        assert "ocrd-tesserocr-segment-line" in PROCESSORS_CONFIG
        assert "ocrd-tesserocr-segment-word" in PROCESSORS_CONFIG
        assert "ocrd-tesserocr-crop" in PROCESSORS_CONFIG
        assert "ocrd-tesserocr-deskew" in PROCESSORS_CONFIG
        assert "ocrd-tesserocr-binarize" in PROCESSORS_CONFIG

    def test_tesserocr_information(self):
        """Check if tesserocr processor is visible."""
        response = self.client.get("/processors")
        self.assert200(response)
        self.assert_template_used("processors.html")
        assert b"ocrd-tesserocr-deskew" in response.data

    def test_tesserocr_parameters(self):
        """Check if ocr_tesserocr is importable."""
        parameters = PROCESSORS_ACTION["ocrd-tesserocr-recognize"]["parameters"]
        assert "textequiv_level" in parameters
        assert parameters["textequiv_level"] == "word"
        assert parameters["overwrite_segments"] is False
        parameters = PROCESSORS_ACTION["ocrd-tesserocr-segment-word"]["parameters"]
        assert parameters["overwrite_words"] is True
        # assert "model" not in parameters

    def test_calamari_integration(self):
        """Check if ocr_calamari is importable."""
        assert "ocrd-calamari-recognize" in PROCESSORS_CONFIG
        assert "ocrd-calamari-recognize" in PROCESSOR_NAMES
        assert PROCESSORS_CONFIG["ocrd-calamari-recognize"]["executable"] == "ocrd-calamari-recognize"

    def test_calamari_information(self):
        """Check if calamari processor is visible."""
        response = self.client.get("/processors")
        self.assert200(response)
        self.assert_template_used("processors.html")
        assert b"ocrd-calamari-recognize" in response.data
