# -*- coding: utf-8 -*-

"""Testing the processor chains for `ocrd_butler` package."""

import pytest

from flask_restplus import fields

from ocrd_butler.api.chain_config import chain_config
from ocrd_butler.api.chains import processor_chains
from ocrd_butler.api.models import chain_model


def test_chain_model():
    assert "id" in chain_model
    assert "name" in chain_model
    assert "description" in chain_model
    assert "processors" in chain_model

    for field in chain_model:
        if field != "processors":
            assert type(chain_model[field]) == fields.String
        else:
            assert type(chain_model[field]) == fields.List


def test_chains_configuration():
    """ Test our chain definition. """
    processors = chain_config.keys()
    assert "TesserocrSegmentRegion" in processors
    assert "TesserocrSegmentLine" in processors
    assert "TesserocrSegmentWord" in processors
    assert "TesserocrRecognize" in processors

    assert chain_config["TesserocrRecognize"]["parameter"]["model"] == "deu"


def test_predefined_chains():
    """ Test our chain definition. """
    assert len(processor_chains) == 1

    tesserocr_chain = processor_chains[0]
    processors = [list(p.keys())[0] for p in tesserocr_chain["processors"]]
    assert "TesserocrRecognize" in processors
