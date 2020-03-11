# -*- coding: utf-8 -*-

"""Restx task routes."""
import json
import uuid

from flask import (
    make_response,
    jsonify,
    request
)
from flask_restx import (
    Resource,
    marshal
)

from celery.signals import task_success
from sqlalchemy.orm.exc import NoResultFound

from ocrd_validators import ParameterValidator

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import task_model
from ocrd_butler.api.processors import PROCESSORS_CONFIG

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task

from ocrd_butler.execution.tasks import run_task

task_namespace = api.namespace("tasks", description="Manage OCR-D Tasks")

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

# frontend:
# - success event could push to frontend and change rotator gif that indicates the work
# - downloadable and (even better) live log showing


class TasksBase(Resource):
    """Base methods for tasks."""

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self.get_actions = ("status", "results")
        self.post_actions = ("run", "rerun", "stop")

    def task_data(self, json_data):
        """ Validate and prepare task input. """
        data = marshal(data=json_data, fields=task_model, skip_none=False)

        if "parameters" not in data or data["parameters"] is None:
            data["parameters"] = {}

        if data["chain_id"] is None:
            task_namespace.abort(400, "Wrong parameter.",
                                 status="Missing chain for task.",
                                 statusCode="400")
        else:
            chain = db_model_Chain.query.filter_by(id=data["chain_id"]).first()
            if chain is None:
                task_namespace.abort(400, "Wrong parameter.",
                                     status="Unknow chain with id {}.".format(
                                         data["chain_id"]),
                                     statusCode="400")

        for processor in data["parameters"].keys():
            validator = ParameterValidator(PROCESSORS_CONFIG[processor])
            report = validator.validate(data["parameters"][processor])
            if not report.is_valid:
                task_namespace.abort(
                    400, "Wrong parameter.",
                    status="Unknown parameter \"{0}\" for processor \"{1}\".".format(
                        data["parameters"][processor], processor),
                    statusCode="400")

        data["parameters"] = json.dumps(data["parameters"])
        data["uid"] = uuid.uuid4().__str__()

        return data


@task_namespace.route("")
class Task(TasksBase):

    @api.doc(responses={201: "Created", 400: "Missing parameter"})
    @api.expect(task_model)
    def post(self):

        data = self.task_data(request.json)

        task = db_model_Task(**data)
        db.session.add(task)
        db.session.commit()

        headers = dict(Location="/tasks/{0}".format(task.id))

        return make_response({
            "message": "Task created.",
            "id": task.id,
        }, 201)


@task_namespace.route("/<string:task_id>/<string:action>")
class TaskActions(TasksBase):
    """Run actions on the task, e.g. run, rerun, stop."""

    @api.doc(responses={200: "OK", 400: "Unknown action",
                        404: "Unknown task", 500: "Error"})
    def post(self, task_id, action):
        """ Execute the given action for the task. """
        # TODO: Return the actions as OPTIONS.
        task = db_model_Task.query.filter_by(id=task_id).first()
        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status="Unknown task for id \"{0}\".".format(task_id),
                statusCode="404")

        if action not in self.post_actions:
            task_namespace.abort(
                400, "Unknown action.",
                status="Unknown action \"{0}\".".format(action),
                statusCode="400")

        action = getattr(self, action)
        try:
            return action(task)
        except Exception as exc:
            task_namespace.abort(
                500, "Error.",
                status="Unexpected error \"{0}\".".format(exc.__str__()),
                statusCode="400")

    @api.doc(responses={200: "OK", 400: "Unknown action",
                        404: "Unknown task", 500: "Error"})
    def get(self, task_id, action):
        """ Get some information for the task. """
        # TODO: Return the actions as OPTIONS.
        task = db_model_Task.query.filter_by(id=task_id).first()
        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status="Unknown task for id \"{0}\".".format(task_id),
                statusCode="404")

        if action not in self.get_actions:
            task_namespace.abort(
                400, "Unknown action.",
                status="Unknown action \"{0}\".".format(action),
                statusCode="400")

        action = getattr(self, action)
        try:
            return action(task)
        except Exception as exc:
            task_namespace.abort(
                500, "Error.",
                status="Unexpected error \"{0}\".".format(exc.__str__()),
                statusCode="400")

    def run(self, task):
        """ Run this task. """
        # worker_task = run_task.apply_async(args=[task.to_json()], countdown=20)
        # worker_task = run_task(task.to_json())
        worker_task = run_task.delay(task.to_json())
        task.worker_task_id = worker_task.id
        db.session.commit()

        return jsonify({
            "worker_task_id": worker_task.id,
            "status": worker_task.status,
            # "result_dir": worker_task["result_dir"],
            # 'current': worker_task.info.get('current', 0),
            # 'total': worker_task.info.get('total', 1),
            # 'status': worker_task.info.get('status', '')
        })

    def re_run(self, task):
        """ Run this task once again. """
        # Basically delete all and run again.
        pass

    def status(self, task):
        """ Run this task. """
        return jsonify({
            "status": task.status
        })

    def results(self, task):
        """ Run this task. """
        return jsonify(task.results)

    def download_page(self, task):
        """ Download the results of the task as PAGE XML. """
        pass

    def download_alto(self, task):
        """ Download the results of the task as ALTO XML. """
        pass

    def download_txt(self, task):
        """ Download the results of the task as text. """
        pass


@task_namespace.route("/<string:task_id>")
class Task(TasksBase):

    @api.doc(responses={200: "OK", 400: "Unknown task id"})
    def get(self, task_id):
        """ Get the task by given id. """
        task = db_model_Task.query.filter_by(id=task_id).first()

        if task is None:
            task_namespace.abort(
                404, "Wrong parameter",
                status="Can't find a task with the id \"{0}\".".format(
                    task_id),
                statusCode="404")

        return jsonify(task.to_json())

    @api.doc(responses={200: "OK", 404: "Unknown task id"})
    def put(self, task_id):
        res = db_model_Task.query.filter_by(id=task_id)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status="Can't find a task with the id \"{0}\".".format(task_id),
                statusCode="404")

        fields = task.to_json().keys()
        for field in fields:
            if field in request.json:
                setattr(task, field, request.json[field])

        db.session.commit()

        return jsonify({
            "message": "Task \"{0}\" updated.".format(task_id)
        })

    @api.doc(responses={200: "OK", 404: "Unknown task id"})
    def delete(self, task_id):
        """Delete a task."""
        res = db_model_Task.query.filter_by(id=task_id)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status="Can't find a task with the id \"{0}\".".format(task_id),
                statusCode="404")

        message = "Task \"{0}\" deleted.".format(task.id)
        res.delete()
        db.session.commit()

        return jsonify({
            "message": message
        })
