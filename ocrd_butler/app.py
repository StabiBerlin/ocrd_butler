# -*- coding: utf-8 -*-

"""Main module."""

import json
import os
import sys
import subprocess
import time

from flask import Flask, request, jsonify, Blueprint
from flask_restplus import Api, Resource, fields

from celery.signals import task_success

import ocrd_butler
from ocrd_butler import factory
from ocrd_butler.tasks import create_task
from ocrd_butler.util import get_config_json

flask_app = factory.create_app(celery=ocrd_butler.celery)

config_json = get_config_json()
flask_app.config.update(config_json)
if not os.path.exists(flask_app.config["OCRD_BUTLER_RESULTS"]):
    os.makedirs(flask_app.config["OCRD_BUTLER_RESULTS"])

# flask-restplus configuration
app = Api(
    app = flask_app,
    version="v1",
    title="ORC-D Tasks",
    description="OCR-D Tasks API")

name_space = app.namespace(
    "ocrd-tasks",
    description="Manage OCR-D Tasks")

task_model = app.model("Task Model", {
    "id": fields.String(
            required = True,
            description="ID of the work",
            help="Can e.g. be a PPN or a SNP."),
    "mets_url": fields.String(
            required = True,
            description="METS URL of the work",
            help="Full URL is required."),
    "file_grp": fields.String(
            required = False,
            description="The file group in the METS file to start the process chain with.",
            help="Defaults to 'DEFAULT'.",
            default="DEFAULT"),
    "tesseract_model": fields.String(
            required = False,
            description="The model used to do the OCR processing.",
            help="Defaults to 'deu'.",
            default='deu'),
})

# get the status of a task
# get the results of a task - this collect links to the resources like mets files, images, etc.
# stop a running task
# delete a task
# archive a task

# list tasks, all or filtered
# delete tasks, all or filtered (safety?)

@name_space.route("/task/<string:id>")
class OcrdTaskStatusClass(Resource):
    @app.doc(responses={ 200: 'OK', 400: 'Unknown task id', 500: 'Error' },
             params={ 'id': 'id of the task' })
    def get(self, id):
        try:
            task = create_task.AsyncResult(id)
        except KeyError as e:
            name_space.abort(400, e.__doc__,
                             status = "Missing parameter 'id'.",
                             statusCode = "400")

        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            # something went wrong in the background job
            # name_space.abort(400, e.__doc__, status = "Could not retrieve information", statusCode = "400")
            # name_space.abort(500, e.__doc__, status = "Could not retrieve information", statusCode = "500")
            response = {
                'state': task.state,
                'current': 1,
                'total': 1,
                'status': str(task.info),  # this is the exception raised
            }
        return jsonify(response)


@name_space.route("/task")
class OcrdTaskClass(Resource):

    @app.doc(responses={ 201: "Created", 400: "Missing parameter" })
    @app.expect(task_model)
    def post(self):

        task = {}

        try:
            task["id"] = request.json["id"]
        except KeyError as e:
            name_space.abort(400, e.__doc__,
                             status = "Missing parameter 'id'.",
                             statusCode = "400")
        try:
            task["mets_url"] = request.json["mets_url"]
        except KeyError as e:
            name_space.abort(400, e.__doc__,
                             status = "Missing parameter 'mets_url'.",
                             statusCode = "400")

        task["file_grp"] = request.json["file_grp"] if "file_grp" \
            in request.json else task_model["file_grp"].default
        task["tesseract_model"] = request.json["tesseract_model"] if "tesseract_model" \
            in request.json else task_model["tesseract_model"].default

        # worker_task = create_task.apply_async(args=[task], countdown=20)
        worker_task = create_task.delay(task)

        @task_success.connect
        def task_success_handler(sender=None, headers=None, body=None, **kwargs):
            # information about task are located in headers for task messages
            # using the task protocol version 2.
            info = headers if 'task' in headers else body
            print('task_success for task id {info[id]}'.format(
                info=info,
            ))

        return {
            "task_id": worker_task.id,
            "state": worker_task.state,
            # 'current': worker_task.info.get('current', 0),
            # 'total': worker_task.info.get('total', 1),
            # 'status': worker_task.info.get('status', '')
        }

