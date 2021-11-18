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
            "workflow_id": "workflow_id",
            "parameters": "{}"
        })
        headers = {"Content-Type": "application/json"}
        self.client.post("/api/tasks", data=data, headers=headers)

    def setup_mocks(self, mock_task_information, mock_fs, result_num='01'):
        """Setup the mocks for patching task_information and flask_sqlalchemy
           query getter.
        """
        mock_task_information.return_value = {
            "ready": True,
            "status": "SUCCESS",
            "result": {
                "result_dir": f"{CURRENT_DIR}/files/ocr_result_{result_num}",
                "task_id": 23,
                "uid": 42
            }
        }
        mock_fs\
            .return_value.filter_by\
            .return_value.first\
            .return_value = type('', (object,), {
                "workflow_id": 1,
                "uid": 42,
                "worker_task_id": 42,
                "default_file_grp": "DEFAULT",
                "processors": ["ocrd-calamari-recognize"],
                "status": "SUCCESS"
            })()

    def test_api_task_invalid_id(self):
        """ test response for task action API call with non-existant task ID
        """
        assert self.client.get(
            "/api/tasks/bielefeld/run"
        ).status_code == 404

    def _create_task(self, task_id, status="SUCCESS"):
        """ create a new instance of the :class:`~ocrd_butler.database.models.Task`
        model without saving it to session.
        """
        return db_model.create(
            db_model.Task,
            uid=task_id,
            workflow_id="1",
            src="src",
            status=status
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
    def test_api_task_result_not_ready(self, task_model_mock_get):
        """ test response codes for API download call with unfinished result.
        """
        task = self._create_task("23", status="FAILED")
        task_model_mock_get.return_value = task
        assert db_model.Task.get(id="23") == task

        response = self.client.get(
            "/api/tasks/23/download_txt"
        )
        result = json.loads(response.data)
        result["statusCode"] = 400
        result["status"] = 'Action "download_txt" not possible.'
        result["message"] = 'Task not ready yet.'

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
        response = self.client.get(
            "/api/tasks/1/status"
        )
        assert response.status_code == 200
        assert response.data == b'{\n  "status": "SUCCESS"\n}\n'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_download_txt(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)
        response = self.client.get("/api/tasks/foobar/download_txt")
        assert response.status_code == 200
        assert response.content_type == "text/txt; charset=utf-8"
        assert b"deutsehe Solaten und Offriere bei der" in response.data
        response.data.count(b"deutsehe Solaten und Offriere bei der") == 1

        self.setup_mocks(mock_task_information, mock_fs, "02")
        response = self.client.get("/api/tasks/foobar/download_txt")
        assert response.status_code == 200
        assert response.content_type == "text/txt; charset=utf-8"
        assert b"vnd vns des liechtes kinder macht" in response.data
        response.data.count(b"vnd vns des liechtes kinder macht") == 1

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_download_log(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        from flask import current_app
        current_app.config['LOGGER_PATH'] = f"{CURRENT_DIR}/files"
        response = self.client.get("/api/tasks/foobar/download_log")

        assert response.status_code == 200
        assert response.content_type == "text/txt; charset=utf-8"
        assert b"Finished processing task foobar" in response.data

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_results_zip(self, mock_task_information, mock_fs):
        """Check if download result files is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_results")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'

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
    def test_api_task_page_zip_03(self, mock_task_information, mock_fs):
        """Check if download txt is working."""
        self.setup_mocks(mock_task_information, mock_fs, result_num='03')

        response = self.client.get("/api/tasks/foobar/download_page")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'


    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_alto_zip(self, mock_task_information, mock_fs):
        """Check if download alto files is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_alto")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_alto_with_images_zip(self, mock_task_information, mock_fs):
        """Check if download alto files with images is working."""
        self.setup_mocks(mock_task_information, mock_fs)

        response = self.client.get("/api/tasks/foobar/download_alto_with_images")

        assert response.status_code == 200
        assert response.content_type == "application/zip"
        assert response.data[:10] == b'PK\x03\x04\x14\x00\x00\x00\x00\x00'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    @mock.patch("ocrd_butler.api.tasks.task_information")
    def test_api_task_page_to_alto(self, mock_task_information, mock_fs):
        """Check if page to alto conversion is working."""
        self.setup_mocks(mock_task_information, mock_fs, result_num="02")

        response = self.client.post("/api/tasks/foobar/page_to_alto")

        assert response.status_code == 200
        assert response.content_type == "application/json"
        assert response.json == {
            'msg': 'You can get the results via http://localhost/api/tasks/42/download_alto',
            'status': 'SUCCESS'
        }
