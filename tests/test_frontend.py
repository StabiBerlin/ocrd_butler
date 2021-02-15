# -*- coding: utf-8 -*-
"""
Testing the frontend of `ocrd_butler` package.
"""

import json
import os
from unittest import mock
from flask_testing import TestCase

import responses
from requests_html import HTML

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import (
    create_app,
    db
)
from ocrd_butler.database.models import Task as db_model_Task


class FrontendTests(TestCase):
    """Test our frontend."""

    def setUp(self):
        db.create_all()

        def create_api_task_callback(request):
            db_task = db_model_Task(
                uid="id",
                src="mets_url",
                default_file_grp="file_grp",
                worker_task_id="worker_task.id",
                chain_id="chain.id",
                parameters="")
            db.session.add(db_task)
            db.session.commit()
            headers = {}
            # "message": "Task created."
            return (201, headers, json.dumps({"task_id": 1, "created": True}))

        def delete_api_task_callback(request):
            db_model_Task.query.filter_by(id=1).delete()
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_app(self):
        return create_app(config=TestingConfig)

    def test_task_page(self):
        """Check if tasks page is visible."""
        response = self.client.get("/tasks")
        self.assert200(response)
        self.assert_template_used("tasks.html")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > th')) == 10
        assert len(html.find('table > tr > td')) == 0

    def get_chain_id(self):
        chain_response = self.client.post("/api/chains", json=dict(
            name="TC Chain",
            description="Chain with tesseract and calamari recog.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-calamari-recognize"
            ]
        ))
        return chain_response.json["id"]

    @responses.activate
    def test_create_task(self):
        """Check if task will be created."""
        self.client.post("/new-task", data=dict(
            task_id="foobar",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            chain_id=self.get_chain_id()
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10
        assert html.find('table > tr > td')[6].text == "worker_task.id"
        self.client.get("/task/delete/1")

    @responses.activate
    def test_delete_task(self):
        """Check if task will be deleted."""

        self.client.post("/new-task", data=dict(
            task_id="foobar-del",
            description="barfoo",
            src="http://foo.bar/mets.xml",
            chain_id=self.get_chain_id()
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
            "data": b"foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/page/42")

        assert response.status_code == 200
        assert response.data[:10] == b"foobar"

    @mock.patch("requests.get")
    def test_frontend_pageviewer_zip(self, mock_requests_get):
        """Check if download files for pageviewer is working."""

        mock_requests_get.return_value = type('', (object,), {
            "data": b"foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/pageviewer/42")

        assert response.status_code == 200
        assert response.data[:10] == b"foobar"

    @mock.patch("requests.get")
    def test_frontend_alto_zip(self, mock_requests_get):
        """Check if download alto files is working."""

        mock_requests_get.return_value = type('', (object,), {
            "data": b"foobar",
            "status_code": 200
        })()

        response = self.client.get("/download/alto/42")

        assert response.status_code == 200
        assert response.data[:10] == b"foobar"
