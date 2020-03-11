# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import pytest

from flask_restx import fields
from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import chain_model
from ocrd_butler.api.models import ChainParametersField


class ApiTests(TestCase):
    """Test our api."""

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_create_new_chain(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        assert response.status_code == 201
        assert response.json["message"] == "Chain created."
        assert response.json["id"] is not None

    def test_create_chain_with_unknown_processor(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(
            name="chain", processors=["foobar"]))
        assert response.status_code == 400
        assert response.json["message"] == "Wrong parameter."
        assert response.json["status"] == 'Unknown processor "foobar".'

    def test_create_chain_without_processor(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(name="chain"))
        assert response.status_code == 400
        assert response.json["message"] == "Wrong parameter."
        assert response.json["status"] == "Missing processors for chain."

    def test_create_chain_with_default_parameters(self):
        """Check if a new chain is created."""
        self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-tesserocr-segment-region",
                        "ocrd-tesserocr-segment-line",
                        "ocrd-tesserocr-segment-word",
                        "ocrd-tesserocr-recognize"]
        ))
        response = self.client.get("/api/chains/1")
        assert "ocrd-tesserocr-segment-region" in response.json["parameters"].keys()
        assert response.json["parameters"]["ocrd-tesserocr-recognize"]["textequiv_level"] == "line"
        assert response.json["parameters"]["ocrd-tesserocr-recognize"]["overwrite_words"] is False

    def test_create_chain_with_own_parameters(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-olena-binarize"],
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                }
            }
        ))

        response = self.client.get("/api/chains/1")
        assert "ocrd-olena-binarize" in response.json["parameters"].keys()
        assert response.json["parameters"]["ocrd-olena-binarize"]["impl"] == "sauvola-ms-split"

    def test_create_chain_with_wrong_parameters(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-olena-binarize"],
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "foobar"
                }
            }
        ))
        assert response.status_code == 400
        # OCR-D validator updates all parameters with default values.
        assert response.status == "400 BAD REQUEST"
        assert response.json["status"].startswith("Unknown parameter \"{\'impl\': \'foobar\',")

    def test_get_chain(self):
        """Check if an existing chain is returned."""
        response = self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-olena-binarize"],
        ))
        response = self.client.get("/api/chains/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Chain"
        assert response.json["description"] == "Some foobar chain."
        assert "ocrd-olena-binarize" in response.json["processors"]

    def test_delete_chain(self):
        """Check if a new chain is created."""
        response = self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        response = self.client.delete("/api/chains/1")
        assert response.status_code == 200
        assert response.json["message"] == "Chain \"New Chain(1)\" deleted."

    def test_delete_unknown_chain(self):
        """Check if a new chain is created."""
        response = self.client.delete("/api/chains/13")
        assert response.status_code == 404
        assert response.json["status"] == "Can't find a chain with the id \"13\"."


    def test_get_unknown_chain(self):
        """Check if a non existing chain ...."""
        response = self.client.get("/api/chains/23")
        assert response.status_code == 404
        assert response.json["status"] == "Can't find a chain with the id \"23\"."

    def test_get_chains(self):
        """Check if a new chain can be retrieved."""
        response = self.client.post("/api/chains", json=dict(
            name="First Chain",
            description="Some foobar chain.",
            processors=["ocrd-olena-binarize"],
        ))
        response = self.client.post("/api/chains", json=dict(
            name="Second Chain",
            description="Some barfoo chain.",
            processors=["ocrd-sbb-textline-detector"],
        ))
        response = self.client.get("/api/chains")

        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]["id"] == 1
        assert response.json[0]["name"] == "First Chain"
        assert response.json[0]["description"] == "Some foobar chain."
        assert "ocrd-olena-binarize" in response.json[0]["processors"]
        assert response.json[1]["id"] == 2
        assert response.json[1]["name"] == "Second Chain"
        assert response.json[1]["description"] == "Some barfoo chain."
        assert "ocrd-sbb-textline-detector" in response.json[1]["processors"]

    def test_update_chain(self):
        """Check if a new chain is created."""
        self.client.post("/api/chains", json=dict(
            name="New Chain",
            description="Some foobar chain.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        response = self.client.get("/api/chains/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Chain"
        assert response.json["description"] == "Some foobar chain."
        assert "ocrd-tesserocr-recognize" in response.json["processors"]

        response = self.client.put("/api/chains/1", json=dict(
            name="Updated Chain",
            description="Some barfoo chain.",
            processors=["ocrd-tesserocr-segment-word"],
        ))
        response = self.client.get("/api/chains/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "Updated Chain"
        assert response.json["description"] == "Some barfoo chain."
        assert "ocrd-tesserocr-recognize" not in response.json["processors"]
        assert "ocrd-tesserocr-segment-word" in response.json["processors"]

    def test_chain_model(self):
        assert "name" in chain_model
        assert "description" in chain_model
        assert "processors" in chain_model

        for field in chain_model:
            if field == "processors":
                assert type(chain_model[field]) == fields.List
            elif field == "parameters":
                assert type(chain_model[field]) == ChainParametersField
            else:
                assert type(chain_model[field]) == fields.String


