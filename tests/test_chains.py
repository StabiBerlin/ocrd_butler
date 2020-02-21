# -*- coding: utf-8 -*-

"""Testing the processor chains for `ocrd_butler` package."""

import pytest

from flask_restplus import fields

from ocrd_butler.api.processors import PROCESSOR_NAMES
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.api.chains import processor_chains
from ocrd_butler.api.models import chain_model


def test_chain_model():
    assert "name" in chain_model
    assert "description" in chain_model
    assert "processors" in chain_model

    for field in chain_model:
        if field != "processors":
            assert type(chain_model[field]) == fields.String
        else:
            assert type(chain_model[field]) == fields.List


def test_processor_names():
    """ Test our chain definition. """
    assert "ocrd-olena-binarize" in PROCESSOR_NAMES
    assert "ocrd-tesserocr-recognize" in PROCESSOR_NAMES
    assert "ocrd-dinglehopper" in PROCESSOR_NAMES
    assert "ocrd-calamari-recognize" in PROCESSOR_NAMES
    assert "ocrd-segment-repair" in PROCESSOR_NAMES
    assert "ocrd-keraslm-rate" in PROCESSOR_NAMES
    assert "ocrd-anybaseocr-binarize" in PROCESSOR_NAMES
    # assert PROCESSORS_ACTION["TesserocrRecognize"]["parameters"]["model"] == "deu"


def test_predefined_chains():
    """ Test our chain definition. """
    assert len(processor_chains) == 1

    tesserocr_chain = processor_chains[0]
    processors = [list(p.keys())[0] for p in tesserocr_chain["processors"]]
    assert "TesserocrRecognize" in processors
