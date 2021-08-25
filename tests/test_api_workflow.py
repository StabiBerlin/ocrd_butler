# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

from flask_restx import fields
from flask_testing import TestCase
from unittest import mock

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import (
    workflow_model,
    WorkflowProcessors,
)

from . import load_mock_workflows


class ApiWorkflowTests(TestCase):
    """Test our api."""

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def get_workflow(self, name="New Workflow", description="Some foobar workflow.",
                     processors=[{"name": "ocrd-tesserocr-recognize"}]):
        workflow = self.client.post("/api/workflows", json=dict(
            name=name,
            description=description,
            processors=processors,
        ))
        return workflow

    def test_create_new_workflow(self):
        """Check if a new workflow is created."""
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
        response = self.get_workflow(processors=[{"name": "foobar"}])
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
            { "name": "ocrd-tesserocr-segment-region" },
            { "name": "ocrd-tesserocr-segment-line" },
            { "name": "ocrd-tesserocr-segment-word" },
            { "name": "ocrd-tesserocr-recognize" },
        ])
        response = self.client.get("/api/workflows/1")
        assert response.json["processors"][0]["name"] == "ocrd-tesserocr-segment-region"
        assert response.json["processors"][3]["parameters"]["textequiv_level"] == "word"
        assert response.json["processors"][3]["parameters"]["overwrite_segments"] is False
        assert response.json["processors"][3]["parameters"]["overwrite_text"] is True

    def test_create_workflow_with_own_parameters(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[{
            "name": "ocrd-olena-binarize",
            "parameters": {
                "impl": "sauvola-ms-split"
            }
        }])
        response = self.client.get("/api/workflows/1")
        processor = response.json["processors"][0]
        assert processor["name"] == "ocrd-olena-binarize"
        assert processor["parameters"]["impl"] == "sauvola-ms-split"
        assert processor["parameters"]["win-size"] == 0
        assert processor["parameters"]["dpi"] == 0

    def test_create_workflow_with_wrong_parameters(self):
        """Check if a new workflow is created."""
        response = self.get_workflow(processors=[{
            "name": "ocrd-olena-binarize",
            "parameters": {
                "impl": "foobar"
            }
        }])
        assert response.status_code == 400
        assert response.status == "400 BAD REQUEST"
        # OCR-D validator updates all parameters with default values.
        assert response.json["message"].startswith(
            "Wrong parameter. Error(s) while validating parameters \"{\'impl\': \'foobar\',")

    def test_create_workflow_global_default_parameters(self):
        """ check if parameter defaults from ocrd_butler.config end up in
        newly created workflow processor.
        """
        wid = self.get_workflow(
            processors=[
                {
                    'name': 'ocrd-tesserocr-recognize',
                    'parameters': {}
                }
            ]
        ).json['id']
        w = self.client.get(f'/api/workflows/{wid}').json
        params = w['processors'][0]['parameters']
        assert 'model' in params
        assert params['model'] == "Fraktur_GT4HistOCR"

    def test_create_workflow_with_reused_processors(self):
        """Check if a workflow with processors that are used multiple is created."""
        foor = self.get_workflow(processors=[
            {"name": "ocrd-olena-binarize"},
            {"name": "ocrd-tesserocr-recognize"},
            {"name": "ocrd-olena-binarize", "parameters": {"impl": "otsu"}},
            {"name": "ocrd-olena-binarize"},
        ])
        response = self.client.get("/api/workflows/1")
        assert response.json["processors"][0]["name"] == "ocrd-olena-binarize"
        assert response.json["processors"][0]["parameters"]["impl"] != "otsu"
        assert response.json["processors"][2]["name"] == "ocrd-olena-binarize"
        assert response.json["processors"][2]["parameters"]["impl"] == "otsu"
        assert response.json["processors"][3]["name"] == "ocrd-olena-binarize"
        assert response.json["processors"][3]["parameters"]["impl"] != "otsu"

    def test_get_workflow(self):
        """Check if an existing workflow is returned."""
        self.get_workflow(processors=[{
            "name": "ocrd-olena-binarize"
        }])
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "New Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert len(response.json["processors"]) == 1
        assert response.json["processors"][0]["name"] == "ocrd-olena-binarize"

    def test_delete_workflow(self):
        """Check if a new workflow is created."""
        self.get_workflow(processors=[{
            "name": "ocrd-tesserocr-recognize"
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

    @mock.patch('ocrd_butler.database.models.Workflow.get_all')
    def test_get_all_workflows(self, model_mock):
        model_mock.return_value = list(
            load_mock_workflows('ocrd_butler/examples/workflows.json')
        )
        response = self.client.get('/api/workflows')
        assert response.status_code == 200
        assert len(response.json) == 5
        assert response.json[0]['description'].startswith('Workflow ')

    def test_get_workflows(self):
        """Check if a new workflow can be retrieved."""
        assert self.get_workflow(name="First Workflow", processors=[{
            "name": "ocrd-olena-binarize"
        }]).status_code == 201
        assert self.get_workflow(name="Second Workflow",
            description="Some barfoo workflow.", processors=[{
                "name": "ocrd-sbb-textline-detector"
        }]).status_code == 201
        response = self.client.get("/api/workflows")
        assert response.status_code == 200
        assert len(response.json) == 2
        assert response.json[0]["id"] == 1
        assert response.json[0]["name"] == "First Workflow"
        assert response.json[0]["description"] == "Some foobar workflow."
        assert response.json[0]["processors"][0]["name"] == "ocrd-olena-binarize"
        assert response.json[0]["processors"][0]["parameters"]["dpi"] == 0
        assert response.json[1]["id"] == 2
        assert response.json[1]["name"] == "Second Workflow"
        assert response.json[1]["description"] == "Some barfoo workflow."
        assert response.json[1]["processors"][0]["name"] == "ocrd-sbb-textline-detector"

    def test_update_workflow(self):
        """Check if a new workflow is created."""
        self.get_workflow(name="First Workflow", processors=[{
            "name": "ocrd-tesserocr-recognize"
        }])
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "First Workflow"
        assert response.json["description"] == "Some foobar workflow."
        assert response.json["processors"][0]["name"] == "ocrd-tesserocr-recognize"

        response = self.client.put("/api/workflows/1", json=dict(
            name="Updated Workflow",
            description="Some barfoo workflow.",
            processors=[{
                "name": "ocrd-tesserocr-segment-word"
            }],
        ))
        assert response.status_code == 201
        response = self.client.get("/api/workflows/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["name"] == "Updated Workflow"
        assert response.json["description"] == "Some barfoo workflow."
        assert response.json["processors"][0]["name"] == "ocrd-tesserocr-segment-word"
        assert response.json['processors'][-1]['output_file_grp'] == (
            '01-OCRD-TESSEROCR-SEGMENT-WORD-OUTPUT'
        )

    def test_amend_workflow(self):
        """ add another processor to existing workflow
        """
        workflow_id = self.get_workflow(
            name='olena',
            processors=[
                {
                    'name': 'ocrd-olena-binarize',
                    'input_file_grp': 'OCR-D-IMG',
                    'output_file_grp': 'OCR-D-IMG-BIN',
                },
            ]
        ).json.get('id')
        assert workflow_id == 1
        response = self.client.put(
            '/api/workflows/1/add',
            json={
                'name': 'ocrd-tesserocr-segment-region',
                'output_file_grp': 'OCR-D-SEG-BLOCK',
            }
        )
        assert response.status_code == 201
        w = self.client.get('/api/workflows/1').json
        assert len(w['processors']) == 2
        assert w['processors'][0]['input_file_grp'] == 'OCR-D-IMG'
        assert w['processors'][-1]['output_file_grp'] == 'OCR-D-SEG-BLOCK'

    def test_workflow_model(self):
        assert "name" in workflow_model
        assert "description" in workflow_model
        assert "processors" in workflow_model
        for field in workflow_model:
            if field == "processors":
                assert type(workflow_model[field]) == WorkflowProcessors
            else:
                assert type(workflow_model[field]) == fields.String
