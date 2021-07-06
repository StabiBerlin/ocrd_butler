# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

from flask_restx import fields
from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import (
    workflow_model,
    WorkflowProcessors,
)


class ApiTests(TestCase):
    """Test our api."""

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def get_workflow(self, name="New Workflow", description="Some foobar workflow.",
                     processors=[{"ocrd-tesserocr-recognize": {}}]):
        workflow = self.client.post("/api/workflows", json=dict(
            name=name,
            description=description,
            processors=processors,
        ))
        return workflow

    def test_create_new_workflow(self):
        """Check if a new workflow is createdOrderedDict."""
        response = self.get_workflow()
        assert response.status_code == 201
        assert response.json["message"] == "Workflow created."
        assert response.json["id"] is not None
        assert response.json["uid"] is not None

    def test_create_workflow_with_wrong_processors_type(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors="foobar")
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        assert response.json["message"] == "Input payload validation failed"
        assert response.json["errors"] == {'processors': "'foobar' is not of type 'array'"}


    def test_create_workflow_with_wrong_processor_format(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=["foobar"])
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        assert response.json["message"] == 'Wrong parameter. Unknown processor "foobar".'

    def test_create_workflow_with_unknown_processor(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[{"foobar": {}}])
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        assert response.json["message"] == 'Wrong parameter. Unknown processor "foobar".'

    def test_create_workflow_without_processor(self):
        """Check if a new workflow is created."""
        response = self.client.post("/api/workflows", json=dict(name="workflow"))
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        assert response.json["message"] == "Input payload validation failed"
        assert response.json["errors"] == {'processors': "'processors' is a required property"}

    def test_create_workflow_with_empty_processor(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[])
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        assert response.json["message"] == 'Wrong parameter. Processors "[]" seems empty.'

    def test_create_workflow_with_default_parameters(self):
        """Check if a new workflow is created."""
        self.get_workflow(processors=[
            { "ocrd-tesserocr-segment-region": {} },
            { "ocrd-tesserocr-segment-line": {} },
            { "ocrd-tesserocr-segment-word": {} },
            { "ocrd-tesserocr-recognize": {} }
        ])
        response = self.client.get("/api/workflows/1")
        assert "ocrd-tesserocr-segment-region" in response.json["processors"].keys()
        assert response.json["processors"]["ocrd-tesserocr-recognize"]["textequiv_level"] == "word"
        assert response.json["processors"]["ocrd-tesserocr-recognize"]["overwrite_segments"] is False
        assert response.json["processors"]["ocrd-tesserocr-segment-word"]["overwrite_words"] is True

    def test_create_workflow_with_own_parameters(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[{
            "ocrd-olena-binarize": {
                "impl": "sauvola-ms-split"
            }
        }])
        response = self.client.get("/api/workflows/1")
        assert "ocrd-olena-binarize" == list(response.json["processors"])[0]
        processor = response.json["processors"]["ocrd-olena-binarize"]
        assert processor["impl"] == "sauvola-ms-split"
        assert processor["k"] == 0.34
        assert processor["win-size"] == 0
        assert processor["dpi"] == 0

    def test_create_workflow_with_wrong_parameters(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[{
            "ocrd-olena-binarize": {
                "impl": "foobar"
            }
        }])
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        # OCR-D validator updates all parameters with default values.
        assert response.json["message"].startswith(
            "Wrong parameter. Error(s) while validating parameters \"{\'impl\': \'foobar\',")

    def test_get_workflow(self):
        """Check if an existing workflow is returned."""
        self.get_workflow(processors=[{
            "ocrd-olena-binarize": {}
        }])
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert len(response.json["processors"]) == 1
        assert list(response.json["processors"])[0] == "ocrd-olena-binarize"

    def test_delete_workflow(self):
        """Check if a new workflow is created."""
        self.get_workflow(processors=[{
            "ocrd-tesserocr-recognize": {}
        }])
        response = self.client.delete("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["message"] == "Delete workflow \"New Workflow(1)\": success"
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 404

    def test_delete_unknown_workflow(self):
        """Check if a new workflow is created."""
        response = self.client.delete("/api/workflows/13")
        assert response.status_code == 404
        assert response.status == "404 NOT FOUND"
        assert response.json["message"].startswith("Can't find a workflow with the id \"13\".")

    def test_get_unknown_workflow(self):
        """Check if a non existing workflow ...."""
        response = self.client.get("/api/workflows/23")
        assert response.status_code == 404
        assert response.status == "404 NOT FOUND"
        assert response.json["message"].startswith("Can't find a workflow with the id \"23\".")

    def test_get_workflows(self):
        """Check if a new workflow can be retrieved."""
        assert self.get_workflow(name="First Workflow", processors=[{
            "ocrd-olena-binarize": {}
        }]).status_code == 201
        assert self.get_workflow(name="Second Workflow",
            description="Some barfoo workflow.", processors=[{
                "ocrd-sbb-textline-detector": {}
        }]).status_code == 201
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
        assert "ocrd-sbb-textline-detector" in list(response.json[1]["processors"])

    def test_update_workflow(self):
        """Check if a new workflow is created."""
        self.get_workflow(name="First Workflow", processors=[{
            "ocrd-tesserocr-recognize": {}
        }])
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "First Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert "ocrd-tesserocr-recognize" in list(response.json["processors"])

        response = self.client.put("/api/workflows/1", json=dict(
            name="Updated Workflow",
            description="Some barfoo workflow.",
            processors=[{"ocrd-tesserocr-segment-word": {}}],
        ))
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "Updated Workflow"
        assert response.json["description"] == "Some barfoo workflow."
        assert "ocrd-tesserocr-recognize" not in list(response.json["processors"])
        assert "ocrd-tesserocr-segment-word" in list(response.json["processors"])

        response = self.client.put("/api/workflows/1", json=dict(
            name="Again updated Workflow",
        ))

    def test_workflow_model(self):
        assert "name" in workflow_model
        assert "description" in workflow_model
        assert "processors" in workflow_model
        for field in workflow_model:
            if field == "processors":
                assert type(workflow_model[field]) == WorkflowProcessors
            else:
                assert type(workflow_model[field]) == fields.String
