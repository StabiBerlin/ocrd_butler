# -*- coding: utf-8 -*-
"""
Testing the frontend of `ocrd_butler` package.
"""

import json
from unittest import mock
from flask_testing import TestCase

import responses
from requests_html import HTML

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import (
    create_app,
    db
)
from ocrd_butler.database import models

from . import load_mock_workflows


class FrontendTests(TestCase):
    """Test our frontend."""

    def setUp(self):
        db.create_all()

        def create_api_task_callback(request):
            db_task = models.Task.create(
                uid="id",
                src="mets_url",
                default_file_grp="file_grp",
                worker_task_id="worker_task.id",
                workflow_id="workflow.id",
                parameters="")
            db.session.add(db_task)
            db.session.commit()
            headers = {}
            # "message": "Task created."
            return (201, headers, json.dumps({"task_id": 1, "created": True}))

        def delete_api_task_callback(request):
            models.Task.query.filter_by(id=1).delete()
            db.session.commit()
            return (200, {}, json.dumps({"task_id": 1, "deleted": True}))

        responses.add_callback(
            responses.POST, "http://localhost/api/tasks",
            callback=create_api_task_callback)

        responses.add(responses.GET, "http://foo.bar/mets.xml",
                      body="<xml>foo</xml>", status=200)

        responses.add_callback(
            responses.DELETE, "http://localhost/api/tasks/1",
            callback=delete_api_task_callback)

        def api_get_taskinfo_callback(request):
            return (200, {}, json.dumps({
                "task_id": 1,
                "state": "PENDING",
                "result": None,
            }))

        responses.add_callback(
            responses.GET, "http://localhost:5555/api/task/info/worker_task.id",
            callback=api_get_taskinfo_callback)

        responses.add(
            method=responses.POST,
            url="http://localhost/api/tasks/1/run",
            body=json.dumps({
                "worker_task_id": "1",
                "status": "SUCCESS",
            }),
            status=200
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def _create_task(self, uid):
        """ Create a new instance of the :class:`~ocrd_butler.database.models.Task`
        model without saving it to session.
        """
        task = models.Task.create(
            uid=uid,
            workflow_id="1",
            src="src",
        )
        task.id = uid
        return task

    @mock.patch("ocrd_butler.database.models.Task.get_all")
    @mock.patch("ocrd_butler.frontend.tasks.task_information")
    def test_task_page(self, mock_task_information, mock_get_all):
        """Check if tasks page is visible."""
        mock_get_all.return_value = [
            self._create_task(uid) for uid in "123"
        ]
        mock_task_information.return_value = {
            "ready": True,
            "result": {
                "ready": True,
                "status": "SUCCESS",
                "succeeded": 1,
                "runtime": 42
            },
            "received": 23,
            "started": 42,
            "succeeded": 666,
            "runtime": 451
        }

        response = self.client.get("/tasks")
        self.assert200(response)
        self.assert_template_used("tasks.html")
        html = HTML(html=response.data)

        assert len(html.find("table > tr > th")) == 10
        assert len(html.find("table > tr > td")) == 30

        download_links = html.find("table > tr:nth-child(2) > td:nth-child(9) > a")
        assert download_links[0].links == {'/download/page/1'}
        assert download_links[1].links == {'/download/alto/1'}
        assert download_links[2].links == {'/download/txt/1'}

    def get_workflow_id(self):
        """Create a workflow for the tests."""
        workflow_response = self.client.post("/api/workflows", json=dict(
            name="TC Workflow",
            description="Workflow with tesseract and calamari recog.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-calamari-recognize"
            ]
        ))
        return workflow_response.json["id"]

    @responses.activate
    def test_create_task(self):
        """Check if task will be created."""
        self.client.post("/new-task", data=dict(
            task_id="foobar",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            workflow_id=self.get_workflow_id(),
            default_file_grp="file_grp"
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10
        assert html.find('table > tr > td')[2].text == "file_grp"
        assert html.find('table > tr > td')[6].text == "worker_task.id"
        self.client.get("/task/delete/1")

    @responses.activate
    def test_delete_task(self):
        """Check if task will be deleted."""

        self.client.post("/new-task", data=dict(
            task_id="foobar-del",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            workflow_id=self.get_workflow_id()
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10

        delete_link = html.find('table > tr > td > a.delete-task')[0].attrs["href"]
        assert delete_link == "/task/delete/1"
        response = self.client.get(delete_link)
        assert response.status == '302 FOUND'
        assert response.status_code == 302

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 0

    @responses.activate
    def test_frontend_run_task(self):
        """ Test whether frontend view calls correct API endpoint.
        """
        response = self.client.get("/task/run/1")
        assert response.status_code == 302
        assert response.headers.get('Location').endswith('/tasks')

    @mock.patch("requests.get")
    def test_frontend_download_txt(self, mock_requests_get):
        """Check if download txt is working."""

        mock_requests_get.return_value = type('', (object,), {
            "text": "foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/txt/42")

        assert response.status_code == 200
        assert response.data == b"foobar"

    @mock.patch("requests.get")
    def test_frontend_page_zip(self, mock_requests_get):
        """Check if download page files is working."""

        mock_requests_get.return_value = type('', (object,), {
            "content": b"foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/page/42")

        assert response.status_code == 200
        assert response.data[:10] == b"foobar"

    @mock.patch("requests.get")
    def test_frontend_page_zip_error(self, mock_requests_get):
        """ Check whether download page requests yields redirect if
        something goes wrong.
        """
        mock_requests_get.return_value = type(
            '', (object,),
            {
                "status_code": 404,
                "content": json.dumps(
                    {
                        "status": "Unknown task for id \"23\".",
                        "statusCode": "404",
                        "message": (
                            "Unknown task. You have requested this URI"
                            " [/api/tasks/23/download_page] but did you mean"
                            " /download/page/<string:task_id> ?"
                        )
                    }
                ),
            }
        )()
        response = self.client.get('/download/page/23')
        assert response.status_code == 302
        assert response.headers.get('Location').endswith('/tasks')

    @mock.patch("requests.get")
    def test_frontend_alto_zip(self, mock_requests_get):
        """Check if download alto files is working."""

        mock_requests_get.return_value = type('', (object,), {
            "content": b"foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/alto/42")

        assert response.status_code == 200
        assert response.data[:10] == b"foobar"

    @mock.patch("ocrd_butler.database.models.Task.get_all")
    def test_frontend_compare_select(self, db_model_task_mock_get_all):
        db_model_task_mock_get_all.return_value = [
            models.Task.create(**{
                "uid": "1",
                "workflow_id": "1",
                "src": "src",
            })
        ]
        response = self.client.get("/compare")
        assert response.status_code == 200

    @mock.patch("ocrd_butler.database.models.Task.get")
    def test_frontend_compare(self, db_model_task_mock_get):
        db_model_task_mock_get.return_value = models.Task.create(
            **{
                'uid': '1', 'workflow_id': '1', 'src': 'src',
            }
        )
        # response = self.client.post(
        #     "/compare",
        #     data={
        #         "task_from": "1",
        #         "task_to": "1",
        #     }
        # )
        # assert response.status_code == 200
        # assert db_model_task_mock_get.call_count == 2

    @mock.patch("requests.get")
    def test_frontend_workflows(self, mock_requests_get):
        workflows = list(
            load_mock_workflows('ocrd_butler/examples/workflows.json')
        )
        assert len(workflows) == 5
        assert type(workflows[0]) == models.Workflow
        mock_requests_get.return_value = type('', (object,), {
            "json": [workflow.to_json() for workflow in workflows],
            "status_code": 200
        })
        response = self.client.get("/workflows")
        assert response.status_code == 200
        html = HTML(html=response.data)
        assert html.find(
            'body > div > div > div > h3:nth-child(2) > a'
        )[0].attrs['href'] == '/workflow/delete/1'

    @mock.patch("requests.delete")
    @mock.patch("requests.get")
    def test_frontend_delete_workflow(self, requests_get, requests_delete):
        requests_get.response_value = type('', (object, ), {
            'status_code': 200,
            'json': list(
                load_mock_workflows('ocrd_butler/examples/workflows.json')
            )[0].to_json(),
        })
        requests_delete.response_value = type('', (object, ), {
            'status_code': 200
        })
        workflow_id = self.get_workflow_id()
        assert workflow_id == 1
        response = self.client.get(f"/workflow/delete/{workflow_id}")
        assert response.status_code == 302

        requests_delete.response_value = type('', (object, ), {
            'status_code': 404
        })
        response = self.client.get("/workflow/delete/XXX")
        assert response.status_code == 404
