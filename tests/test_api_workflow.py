# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

from flask_restx import fields
from flask_testing import TestCase
from unittest import mock

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import (
    workflow_model,
    WorkflowParametersField,
)

from . import load_mock_workflows


class ApiTests(TestCase):
    """Test our api."""

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_create_new_workflow(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        assert response.status_code == 201
        assert response.json["message"] == "Workflow created."
        assert response.json["id"] is not None

    def test_create_workflow_with_unknown_processor(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(
            name="workflow", processors=["foobar"]))
        assert response.status_code == 400
        assert response.json["message"] == "Wrong parameter."
        assert response.json["status"] == 'Unknown processor "foobar".'

    def test_create_workflow_without_processor(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(name="workflow"))
        assert response.status_code == 400
        assert response.json["message"] == "Wrong parameter."
        assert response.json["status"] == "Missing processors for workflow."

    def test_create_workflow_with_default_parameters(self):
        """Check if a new workflow is created."""
        self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-tesserocr-segment-region",
                        "ocrd-tesserocr-segment-line",
                        "ocrd-tesserocr-segment-word",
                        "ocrd-tesserocr-recognize"]
        ))
        response = self.client.get("/api/workflows/1")
        assert "ocrd-tesserocr-segment-region" in response.json["parameters"].keys()
        assert response.json["parameters"]["ocrd-tesserocr-recognize"]["textequiv_level"] == "word"
        assert response.json["parameters"]["ocrd-tesserocr-recognize"]["overwrite_segments"] is False
        assert response.json["parameters"]["ocrd-tesserocr-segment-word"]["overwrite_words"] is True

    def test_create_workflow_with_own_parameters(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-olena-binarize"],
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                }
            }
        ))

        response = self.client.get("/api/workflows/1")
        assert "ocrd-olena-binarize" in response.json["parameters"].keys()
        assert response.json["parameters"]["ocrd-olena-binarize"]["impl"] == "sauvola-ms-split"

    def test_create_workflow_with_wrong_parameters(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
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
        assert response.json["status"].startswith(
            "Error while validating parameters \"{\'impl\': \'foobar\',")

    def test_get_workflow(self):
        """Check if an existing workflow is returned."""
        assert self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-olena-binarize"],
        )).status_code == 201
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert "ocrd-olena-binarize" in response.json["processors"]

    def test_delete_workflow(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        response = self.client.delete("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["message"] == "Delete workflow \"New Workflow(1)\": success"
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 404

    def test_delete_unknown_workflow(self):
        """Check if a new workflow is created."""
        response = self.client.delete("/api/workflows/13")
        assert response.status_code == 404
        assert response.json["status"] == "Can't find a workflow with the id \"13\"."

    def test_get_unknown_workflow(self):
        """Check if a non existing workflow ...."""
        response = self.client.get("/api/workflows/23")
        assert response.status_code == 404
        assert response.json["status"] == "Can't find a workflow with the id \"23\"."

    @mock.patch('ocrd_butler.database.models.Workflow.get_all')
    def test_get_all_chains(self, model_mock):
        model_mock.return_value = list(
            load_mock_workflows('ocrd_butler/examples/workflows.json')
        )
        response = self.client.get('/api/workflows')
        assert response.status_code == 200
        assert len(response.json) == 5
        assert response.json[0]['description'].startswith('Workflow ')

    def test_get_workflows(self):
        """Check if a new workflow can be retrieved."""
        assert self.client.post("/api/workflows", json=dict(
            name="First Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-olena-binarize"],
        )).status_code == 201
        assert self.client.post("/api/workflows", json=dict(
            name="Second Workflow",
            description="Some barfoo workflow.",
            processors=["ocrd-sbb-textline-detector"],
        )).status_code == 201
        response = self.client.get("/api/workflows")

        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]["id"] == 1
        assert response.json[0]["name"] == "First Workflow"
        assert response.json[0]["description"] == "Some foobar workflow."
        assert "ocrd-olena-binarize" in response.json[0]["processors"]
        assert response.json[1]["id"] == 2
        assert response.json[1]["name"] == "Second Workflow"
        assert response.json[1]["description"] == "Some barfoo workflow."
        assert "ocrd-sbb-textline-detector" in response.json[1]["processors"]

    def test_update_workflow(self):
        """Check if a new workflow is created."""
        self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=["ocrd-tesserocr-recognize"],
        ))
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert "ocrd-tesserocr-recognize" in response.json["processors"]

        response = self.client.put("/api/workflows/1", json=dict(
            name="Updated Workflow",
            description="Some barfoo workflow.",
            processors=["ocrd-tesserocr-segment-word"],
        ))
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "Updated Workflow"
        assert response.json["description"] == "Some barfoo workflow."
        assert "ocrd-tesserocr-recognize" not in response.json["processors"]
        assert "ocrd-tesserocr-segment-word" in response.json["processors"]

    def test_workflow_model(self):
        assert "name" in workflow_model
        assert "description" in workflow_model
        assert "processors" in workflow_model

        for field in workflow_model:
            if field == "processors":
                assert type(workflow_model[field]) == fields.List
            elif field == "parameters":
                assert type(workflow_model[field]) == WorkflowParametersField
            else:
                assert type(workflow_model[field]) == fields.String
