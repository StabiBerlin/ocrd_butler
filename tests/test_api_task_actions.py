# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import json
import os
from unittest import mock

from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app
from ocrd_butler.database import models as db_model

CURRENT_DIR = os.path.dirname(__file__)


class ApiTaskActions(TestCase):
    """Test our tasks actions."""

    def create_app(self):
        return create_app(config=TestingConfig)

    def setUp(self):
        data = json.dumps({
            "description": "task_description",
            "src": "src",
            "file_grp": "DEFAULT",
            "chain_id": "chain_id",
            "parameters": "{}"
        })
        headers = {"Content-Type": "application/json"}
        self.client.post("/api/tasks", data=data, headers=headers)

    def setup_mocks(self, mock_task_information, mock_fs):
        """Setup the mocks for patching task_information and flask_sqlalchemy
           query getter.
        """
        mock_task_information.return_value = {
            "ready": True,
            "result": {
                "result_dir": f"{CURRENT_DIR}/files/ocr_result_01",
                "task_id": 23
            }
        }
        mock_fs\
            .return_value.filter_by\
            .return_value.first\
            .return_value = type('', (object,), {
                "chain_id": 1,
                "worker_task_id": 42,
                "processors": ["ocrd-calamari-recognize"]
            })()

    def test_api_task_invalid_id(self):
        """ test response for task action API call with non-existant task ID
        """
        assert self.client.get(
            "/api/tasks/bielefeld/run"
        ).status_code == 404

    def _create_task(self, task_id):
        """ create a new instance of the :class:`~ocrd_butler.database.models.Task`
        model without saving it to session.
        """
        return db_model.create(
            db_model.Task,
            uid=task_id,
            chain_id="1",
            src="src",
        )

    @mock.patch("ocrd_butler.database.models.Task.get")
    def test_api_task_invalid_action(self, task_model_mock_get):
        """ test response codes for API call with unsupported action
        """
        task = self._create_task("1")
        task_model_mock_get.return_value = task
        assert db_model.Task.get(id="1") == task
        assert self.client.get(
            "/api/tasks/1/unsupported_action"
        ).status_code == 400

    @mock.patch("ocrd_butler.database.models.Task.get")
    @mock.patch("ocrd_butler.execution.tasks.run_task")
    def test_api_task_run(self, celery_mock, task_model_mock_get):
        """ test whether run action gets called if task ID and action exist.
        """
        task = self._create_task("2")
        task_model_mock_get.return_value = task
        celery_mock.side_effect = Exception()
        assert self.client.post(
            "/api/tasks/2/run"
        ).status_code == 500
        assert self.client.post(
            "/api/tasks/2/rerun"
        ).status_code == 500

    @mock.patch("ocrd_butler.database.models.Task.get")
    def test_api_task_get_status(self, task_model_mock_get):
        """ test response codes for API for task status
        """
        task = self._create_task("1")
        task_model_mock_get.return_value = task
        assert self.client.get(
            "/api/tasks/1/status"
        ).status_code == 200

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_download_txt(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_txt")

        assert response.status_code == 200
        assert response.content_type == "text/txt; charset=utf-8"
        assert b"nen eer gbaun nonenronrndannn" in response.data

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_page_zip(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_page")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_pageviewer_zip(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_pageviewer")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_alto_zip(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_alto")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'
