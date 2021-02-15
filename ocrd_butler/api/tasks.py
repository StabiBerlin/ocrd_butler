# -*- coding: utf-8 -*-

"""Restx task routes."""
import glob
import io
import json
import pathlib
import os
import uuid
import xml.etree.ElementTree as ET
import zipfile

from flask import (
    make_response,
    jsonify,
    request,
    send_file
)
from flask_restx import (
    Resource,
    marshal
)
import requests

from ocrd_validators import ParameterValidator

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import task_model
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.api.processors import PROCESSORS_CONFIG

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task

from ocrd_butler.execution.tasks import run_task
from ocrd_butler.util import logger, to_json

log = logger(__name__)

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


def task_information(uid):
    """
    Get information for the task based on its uid.
    """
    if uid is None:
        return None

    response = requests.get("http://localhost:5555/api/task/info/{0}".format(uid))
    if response.status_code == 404:
        current_app.logger.warning("Can't find task '{0}'".format(uid))
        return None
    try:
        task_info = json.loads(response.content)
    except json.decoder.JSONDecodeError as exc:
        current_app.logger.error("Can't read response for task '{0}'. ({1})".format(
            uid, exc.__str__()))
        return None

    task_info["ready"] = task_info["state"] == "SUCCESS"
    if task_info["result"] is not None:
        task_info["result"] = json.loads(task_info["result"].replace("'", '"'))

    return task_info


class TasksBase(Resource):
    """Base methods for tasks."""

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self.get_actions = (
            "status",
            "results",
            "download_txt",
            "download_page")
        self.post_actions = ("run", "rerun", "stop")

    def task_data(self, json_data):
        """ Validate and prepare task input. """
        data = marshal(data=json_data, fields=task_model, skip_none=False)

        if "parameters" not in data or data["parameters"] is None:
            data["parameters"] = {}
        data["parameters"] = to_json(data["parameters"])

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
        # worker_task = run_task.apply_async(args=[task.to_json()],
        #                                    countdown=20)
        # worker_task = run_task(task.to_json())
        log.info(f'run task: {task}')
        worker_task = run_task.delay(task.to_json())
        task.worker_task_id = worker_task.id
        db.session.commit()

        result = {
            "worker_task_id": worker_task.id,
            "status": worker_task.status,
            "traceback": worker_task.traceback,
            # "result_dir": worker_task["result_dir"],
            # 'current': worker_task.info.get('current', 0),
            # 'total': worker_task.info.get('total', 1),
            # 'status': worker_task.info.get('status', '')
        }

        return jsonify(result)

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
        task_info = task_information(task.worker_task_id)

        # Get the output group of the last step in the chain of the task.
        task_data = db_model_Task.query.filter_by(worker_task_id=task.worker_task_id).first()
        chain_data = db_model_Chain.query.filter_by(id=task_data.chain_id).first()
        last_step = chain_data.processors[-1]
        last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

        page_xml_dir = os.path.join(task_info["result"]["result_dir"], last_output)
        base_path = pathlib.Path(page_xml_dir)

        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            for f_name in base_path.iterdir():
                arcname = f"{last_output}/{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
        data.seek(0)

        return send_file(
            data,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"ocr_page_xml_{task_info['result']['task_id']}.zip"
        )


    def download_alto(self, task):
        """ Download the results of the task as ALTO XML. """
        pass

    def download_txt(self, task):
        """ Download the results of the task as text. """
        task_info = task_information(task.worker_task_id)

        # Get the output group of the last step in the chain of the task.
        task_data = db_model_Task.query.filter_by(worker_task_id=task.worker_task_id).first()
        chain_data = db_model_Chain.query.filter_by(id=task_data.chain_id).first()
        last_step = chain_data.processors[-1]
        last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

        page_xml_dir = os.path.join(task_info["result"]["result_dir"], last_output)
        fulltext = ""

        namespace = {
            "page_2009-03-16": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2009-03-16",
            "page_2010-01-12": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-01-12",
            "page_2010-03-19": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-03-19",
            "page_2013-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
            "page_2016-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15",
            "page_2017-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15",
            "page_2018-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15",
            "page_2019-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
        }

        files = glob.glob("{}/*.xml".format(page_xml_dir))
        files.sort()

        for file in files:
            tree = ET.parse(file)
            xmlns = tree.getroot().tag.split("}")[0].strip("{")
            if xmlns in namespace.values():
                for regions in tree.iterfind(".//{%s}TextRegion" % xmlns):
                    fulltext += "\n"
                    for content in regions.findall(
                            ".//{%s}TextLine//{%s}TextEquiv//{%s}Unicode" % (xmlns, xmlns, xmlns)):
                        if content.text is not None:
                            fulltext += content.text

        response = make_response(fulltext, 200)
        response.mimetype = "text/txt"
        response.headers.extend({
            "Content-Disposition":
            "attachment;filename=fulltext_%s.txt" % task_info["result"]["task_id"]
        })
        return response


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
