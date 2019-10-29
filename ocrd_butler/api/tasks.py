# -*- coding: utf-8 -*-

"""Restplus task routess."""

from flask import jsonify, request
from flask_restplus import Api, Resource, fields

from celery.signals import task_success

from ocrd_butler.api.restplus import api
from ocrd_butler.api.models import task_model

from ocrd_butler.queue.tasks import create_task

ns = api.namespace(
    "ocrd-tasks",
    description="Manage OCR-D Tasks")

# get the status of a task
# get the results of a task - this collect links to the resources like mets files, images, etc.
# stop a running task
# delete a task
# archive a task

# list tasks, all or filtered
# delete tasks, all or filtered (safety?)

# get predefined chains
# get all usable processors
# get default chain

# have a look to the wording in the context of a butler
# do a butler "serve"?
# take a butler a task or a job?

@ns.route("/task")
class Task(Resource):

    @api.doc(responses={ 201: "Created", 400: "Missing parameter" })
    @api.expect(task_model)
    def post(self):
        task = {}
        try:
            task["id"] = request.json["id"]
        except KeyError as e:
            ns.abort(400, e.__doc__,
                             status = "Missing parameter 'id'.",
                             statusCode = "400")
        try:
            task["mets_url"] = request.json["mets_url"]
        except KeyError as e:
            ns.abort(400, e.__doc__,
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


@ns.route("/task/<string:id>")
class TaskList(Resource):

    @api.doc(responses={ 200: 'OK', 400: 'Unknown task id', 500: 'Error' },
             params={ 'id': 'id of the task' })
    def get(self, id):
        try:
            task = create_task.AsyncResult(id)
        except KeyError as e:
            ns.abort(400, e.__doc__,
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
