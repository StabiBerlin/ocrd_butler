# -*- coding: utf-8 -*-

"""Testing the app of `ocrd_butler` package."""

import pytest
import json
import requests
import responses
from requests_html import HTML

from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.database.models import Task as db_model_Task


class AppTests(TestCase):
    """Test our predefined processors."""

    def setUp(self):
        db.create_all()

        def create_api_task_callback(request):
            db_task = db_model_Task(
                work_id="id",
                mets_url="mets_url",
                file_grp="file_grp",
                worker_id="worker_task.id",
                chain_id="chain.id",
                parameter="")
            db.session.add(db_task)
            db.session.commit()
            resp_body = "foobar"
            headers = {}
            return (200, headers, resp_body)

        def delete_api_task_callback(request):
            db_model_Task.query.filter_by(id=1).delete()
            db.session.commit()
            return (200, {}, json.dumps({"task_id": 1, "deleted": True}))

        responses.add_callback(
            responses.POST, "http://localhost/api/tasks/task",
            callback=create_api_task_callback)

        responses.add(responses.GET, "http://foo.bar/mets.xml",
                      body="<xml>foo</xml>", status=200)

        responses.add_callback(
            responses.DELETE, "http://localhost/api/tasks/task/1",
            callback=delete_api_task_callback)

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

    @responses.activate
    def test_create_task(self):
        """Check if task will be created."""

        self.client.post("/new-task", data=dict(
            id="foobar",
            mets_url="http://foo.bar/mets.xml",
            file_grp="DEFAULT",
            chain="FOOBAR"
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10
        assert html.find('table > tr > td')[6].text == "worker_task.id (('PENDING',))"
        self.client.get("/task/delete/1")

    @responses.activate
    def test_delete_task(self):
        """Check if task will be deleted."""

        self.client.post("/new-task", data=dict(
            id="foobar",
            mets_url="http://foo.bar/mets.xml",
            file_grp="DEFAULT",
            chain="FOOBAR"
        ))

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 10

        delete_link = html.find('table > tr > td > a.delete-task')[0].attrs["href"]
        response = self.client.get(delete_link)
        # self.delete_one_task()

        # assert response.status == "302 FOUND"

        response = self.client.get("/tasks")
        html = HTML(html=response.data)
        assert len(html.find('table > tr > td')) == 0

