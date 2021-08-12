# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

from flask_restx import fields
from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import task_model


class ApiTaskTests(TestCase):
    """Test our api."""

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def workflow(self):
        response = self.client.post("/api/workflows", json=dict(
            name="New Workflow",
            description="Some foobar workflow.",
            processors=[{"name": "ocrd-tesserocr-recognize"}]
        ))
        return response.json["id"]

    def test_create_new_task_mets_src(self):
        """Check if a new task is created."""
        response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.workflow(),
            src="https://foobar.tdl/themets.xml",
            description="Just a task.",
            default_file_grp="THUMBS"
        ))
        assert response.status_code == 201
        assert response.json["message"] == "Task created."
        assert response.json["id"] == 1

        response = self.client.get("/api/tasks/1")
        assert response.status_code == 200
        assert response.json["id"] == 1
        assert response.json["src"] == "https://foobar.tdl/themets.xml"
        assert response.json["description"] == "Just a task."
        assert response.json["default_file_grp"] == "THUMBS"
        assert response.json["status"] == "CREATED"
        assert response.json["results"] == {}

    def test_get_all_tasks(self):
        """ test /api/tasks GET response
        """
        self.client.post(
            '/api/tasks',
            json={
                'workflow_id': self.workflow(),
                'src': 'http://url',
            }
        )
        response = self.client.get('/api/tasks')
        assert response.status_code == 200
        assert len(response.json) == 1

    def test_change_task(self):
        """Check if a new task is created."""
        response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.workflow(),
            src="https://foobar.tdl/themets.xml",
            description="Just a task.",
            default_file_grp="THUMBS"
        ))
        assert response.status_code == 201
        assert response.json["message"] == "Task created."
        assert response.json["id"] == 1

        response = self.client.get("/api/tasks/1")
        assert response.json["src"] == "https://foobar.tdl/themets.xml"

        response = self.client.put("/api/tasks/1", json=dict(
            src="https://barfoo.tdl/themets.xml",
        ))
        response = self.client.get("/api/tasks/1")
        assert response.json["src"] == "https://barfoo.tdl/themets.xml"

    def test_delete_task(self):
        """Check if a task is deleted."""
        self.client.post("/api/tasks", json=dict(
            workflow_id=self.workflow(),
            src="https://foobar.tdl/themets.xml",
            description="Just a task."
        ))

        response = self.client.delete("/api/tasks/1")
        assert response.status_code == 200
        assert response.json["message"] == "Task \"1\" deleted."

        response = self.client.delete("/api/tasks/13")
        assert response.status_code == 404
        assert response.json["message"].startswith("Unknown task")

    def test_task_model(self):
        assert "src" in task_model
        assert "workflow_id" in task_model
        assert "parameters" in task_model
        assert "description" in task_model
        assert "default_file_grp" in task_model
        assert "worker_task_id" in task_model
        assert "status" in task_model
        assert "results" in task_model

        for field in task_model:
            assert type(task_model[field]) == fields.String
