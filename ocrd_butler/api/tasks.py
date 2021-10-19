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
    current_app,
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

from ocrd_page_to_alto.convert import OcrdPageAltoConverter

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import task_model
from ocrd_butler.api.processors import PROCESSORS_CONFIG

from ocrd_butler.database import db
from ocrd_butler.database.models import Workflow as db_model_Workflow
from ocrd_butler.database.models import Task as db_model_Task

from ocrd_butler.execution.tasks import run_task
from ocrd_butler.util import (
    logger,
    to_json,
    host_url,
    flower_url,
    ocr_result_path,
    alto_result_path,
    page_to_alto as page_to_alto_util,
    page_xml_namespaces,
)


task_namespace = api.namespace("tasks", description="Manage OCR-D Tasks")


# get the status of a task
# stop a running task
# delete a task
# archive a task

# list tasks, all or filtered
# delete tasks, all or filtered (safety?)

# get predefined workflows
# get all usable processors
# get default workflow

# have a look to the wording in the context of a butler
# do a butler "serve"?
# take a butler a task or a job?

# frontend:
# - success event could push to frontend and change rotator gif that indicates the work
# - downloadable and (even better) live log showing


def task_information(worker_task_id):
    """
    Get information for the task based on its worker id.
    """
    if worker_task_id is None:
        return None

    flower_base = flower_url(request)
    response = requests.get(f"{flower_base}/api/task/info/{worker_task_id}")
    if response.status_code == 404:
        current_app.logger.warning(f"Can't find task '{worker_task_id}'")
        return None
    try:
        task_info = json.loads(response.content)
    except json.decoder.JSONDecodeError as exc:
        current_app.logger.error(f"Can't read response for task '{worker_task_id}'. ({exc.__str__()})")
        return None

    task_info["ready"] = task_info["state"] == "SUCCESS"
    if task_info["result"] is not None:
        task_info["result"] = json.loads(task_info["result"].replace("'", '"'))

        # task_db_data = db_model_Task.get(worker_task_id=uid)
        # workflow_db_data = db_model_Chain.get(id=task_db_data.workflow_id)
        # last_step = workflow_db_data.processors[-1]
        # last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]
        # task_info["last_output_file_grp"] = last_output

    return task_info


class TasksBase(Resource):
    """Base methods for tasks."""

    def __init__(self, api_obj, *args, **kwargs):
        super().__init__(api_obj, *args, **kwargs)
        self.get_actions = (
            "status",
            "results",
            "download_txt",
            "download_page",
            "download_alto",
            "download_log",
        )
        self.post_actions = (
            "run",
            "rerun",
            "stop",
            "page_to_alto",
        )

    def task_data(self, json_data):
        """ Validate and prepare task input. """
        data = marshal(data=json_data, fields=task_model, skip_none=False)

        if "parameters" not in data or data["parameters"] is None:
            data["parameters"] = {}
        data["parameters"] = to_json(data["parameters"])

        if data["workflow_id"] is None:
            task_namespace.abort(400, "Wrong parameter.",
                                 status="Missing workflow for task.",
                                 statusCode="400")
        else:
            workflow = db_model_Workflow.get(id=data["workflow_id"])
            if workflow is None:
                task_namespace.abort(
                    400, "Wrong parameter.",
                    status=f"Unknown workflow with id {data['workflow_id']}.",
                    statusCode="400"
                )

        for processor in data["parameters"].keys():
            validator = ParameterValidator(PROCESSORS_CONFIG[processor])
            report = validator.validate(data["parameters"][processor])
            if not report.is_valid:
                task_namespace.abort(
                    400, "Wrong parameter.",
                    status=f"Unknown parameter \"{data['parameters'][processor]}\" "
                           f"for processor \"{processor}\".",
                    statusCode="400")

        data["parameters"] = json.dumps(data["parameters"])
        data["uid"] = uuid.uuid4().__str__()

        return data


@task_namespace.route("")
class TaskRoot(TasksBase):
    """Restful methods for tasks."""

    @api.doc(responses={201: "Created", 400: "Missing parameter"})
    @api.expect(task_model)
    def post(self):
        """Create a new Task."""
        task = db_model_Task.add(
            **self.task_data(request.json)
        )

        return make_response({
            "message": "Task created.",
            "id": task.id,
            "uid": task.uid,
        }, 201)

    @api.doc(reponses={200: "Found"})
    def get(self):
        """ Get all tasks.
        """
        return jsonify(
            [
                task.to_json()
                for task in db_model_Task.get_all()
            ]
        )


@task_namespace.route("/<string:task_id>/<string:action>")
class TaskActions(TasksBase):
    """Run actions on the task."""

    @api.doc(responses={200: "OK", 400: "Unknown action",
                        404: "Unknown task", 500: "Error"})
    def post(self, task_id, action):
        """
        Execute the given action for the task.

        Available post actions:
        * run
        * rerun
        * stop
        * page_to_alto

        TODO: Return the actions as OPTIONS.
        """
        logger.info(f"Task {task_id} post action {action} called.")

        task = db_model_Task.get(id=task_id)
        if task is None:
            task = db_model_Task.get(uid=task_id)

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Unknown task for id \"{task_id}\".",
                statusCode="404")

        if action not in self.post_actions:
            task_namespace.abort(
                400, "Unknown action.",
                status=f"Unknown action \"{action}\".",
                statusCode="400")

        action = getattr(self, action)
        try:
            return action(task)
        except Exception as exc:
            task_namespace.abort(
                500, "Error.",
                status=f"Unexpected error \"{exc.__str__()}\".",
                statusCode="400")

    @api.doc(responses={200: "OK", 400: "Unknown action",
                        404: "Unknown task", 500: "Error"})
    def get(self, task_id, action):
        """
        Get information or results of the task.

        Available GET actions:
        * status
        * results
        * download_txt
        * download_page
        * download_alto
        * download_log

        TODO: Return the actions as OPTIONS.
        """
        logger.info(f"Task {task_id} get action {action} called.")

        task = db_model_Task.get(id=task_id)
        if task is None:
            task = db_model_Task.get(uid=task_id)

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Unknown task with id or uid \"{task_id}\".",
                statusCode="404")

        if action not in self.get_actions:
            task_namespace.abort(
                400, "Unknown action.",
                status=f"Unknown action \"{action}\".",
                statusCode="400")

        action = getattr(self, action)
        try:
            return action(task)
        except Exception as exc:
            task_namespace.abort(
                500, "Error.",
                status=f"Unexpected error \"{exc.__str__()}\".",
                statusCode="400")

    def run(self, task: db_model_Task):
        """ Run this task. """
        logger.info(f"Action 'run' called for task: {task.to_json()}")

        # celery_worker_task = run_task(task.to_json())  # use for debugging
        celery_worker_task = run_task.delay(task.to_json())
        # celery_worker_task = run_task.apply_async(args=[task.to_json()],
        #                                    countdown=20)
        # if '__dict__' in dir(celery_worker_task):
        #     # async task result
        #     celery_worker_task = celery_worker_task.__dict__

        task.worker_task_id = celery_worker_task.task_id
        task.status = celery_worker_task.status
        db.session.commit()

        result = {
            "worker_task_id": celery_worker_task.task_id,
            "status": celery_worker_task.status,
            "traceback": celery_worker_task.traceback,
        }

        return jsonify(result)

    def rerun(self, task):
        """ Run this task once again. """
        # Basically delete all and run again.
        raise NotImplementedError

    def status(self, task):
        """ Get the status of this task. """
        return jsonify({
            "status": task.status
        })

    def results(self, task):
        """ Get the results of this task. """
        return jsonify(task.results)

    def page_to_alto(self, task):
        """ Convert page files to alto. """
        task_info = task_information(task.worker_task_id)
        page_to_alto_util(task.uid, task_info['result']['result_dir'])

        return jsonify({
            "status": "SUCCESS",
            "msg": f"You can get the results via {host_url(request)}api/tasks/{task.uid}/download_alto"
        })

    def download_page(self, task):
        """ Download the results of the task for e.g. pageviewer, including PAGE XML,
            METS file and DEFAULT images.
        """
        task_info = task_information(task.worker_task_id)
        page_result_path = ocr_result_path(task_info['result']['result_dir'])

        if page_result_path is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task_info['result']['uid']}"
            })

        img_dir = os.path.join(f"{task_info['result']['result_dir']}/{task.default_file_grp}")
        img_path = pathlib.Path(img_dir)

        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            zip_file.write(f"{task_info['result']['result_dir']}/mets.xml", arcname="mets.xml")
            for f_name in img_path.iterdir():
                arcname = f"{task.default_file_grp}/{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
            for f_name in page_result_path.iterdir():
                arcname = f"{os.path.basename(os.path.dirname(f_name))}/{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
        data.seek(0)

        return send_file(
            data,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"ocr_page_xml_{task_info['result']['uid']}.zip"
        )

    def download_alto(self, task):
        """ Download the results of the task as ALTO XML. """
        task_info = task_information(task.worker_task_id)
        alto_path = alto_result_path(task_info["result"]["result_dir"])
        page_to_alto_util(task.uid, task_info['result']['result_dir'])
        if not os.path.exists(alto_path):
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find alto results for task {task_info['result']['uid']}"
            })

        img_dir = os.path.join(f"{task_info['result']['result_dir']}/{task.default_file_grp}")
        img_path = pathlib.Path(img_dir)
        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            zip_file.write(f"{task_info['result']['result_dir']}/mets.xml", arcname="mets.xml")
            for f_name in img_path.iterdir():
                arcname = f"{task.default_file_grp}/{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
            for f_name in alto_path.iterdir():
                arcname = f"{os.path.basename(os.path.dirname(f_name))}/{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
        data.seek(0)

        return send_file(
            data,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename="ocr_alto_xml_%s.zip" % task_info["result"]["uid"]
        )

    def download_txt(self, task):
        """ Download the results of the task as text. """
        # https://github.com/qurator-spk/dinglehopper/blob/master/qurator/dinglehopper/extracted_text.py#L95
        task_info = task_information(task.worker_task_id)
        page_result_path = ocr_result_path(task_info['result']['result_dir'])

        if page_result_path is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task_info['result']['uid']}"
            })

        fulltext = ""

        files = glob.glob(f"{page_result_path}/*.xml")
        files.sort()
        for file in files:
            tree = ET.parse(file)
            xmlns = tree.getroot().tag.split("}")[0].strip("{")
            if xmlns in page_xml_namespaces.values():
                for regions in tree.iterfind(".//{%s}TextRegion" % xmlns):
                    fulltext += "\n"
                    words = regions.findall(
                        ".//{{{0}}}TextLine//{{{0}}}Word"
                        "//{{{0}}}TextEquiv//{{{0}}}Unicode".format(xmlns))
                    if len(words) == 0:
                        words = regions.findall(
                            ".//{{{0}}}TextLine"
                            "//{{{0}}}TextEquiv//{{{0}}}Unicode".format(xmlns))
                    for index, word in enumerate(words):
                        if word.text is not None:
                            fulltext += word.text
                            if ++index < len(words):
                                fulltext += " "

        response = make_response(fulltext, 200)
        response.mimetype = "text/txt"
        response.headers.extend({
            "Content-Disposition":
            "attachment;filename=fulltext_%s.txt" % task_info["result"]["uid"]
        })
        return response


    def download_log(self, task):
        """ Download the log file of the task. """
        log_file_path = pathlib.Path(
            f"{current_app.config['LOGGER_PATH']}/task-{task.uid}.log"
        )
        if log_file_path is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find log file for task {task.uid}"
            })
        if not os.path.exists(log_file_path):
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find log file for task {task.uid}"
            })

        with open(log_file_path, 'r') as fh:
            data = fh.read()
            fh.close()

        response = make_response(str(data), 200)
        response.mimetype = "text/txt"
        response.headers.extend({
            "Content-Disposition":
            "attachment;filename=fulltext_%s.txt" % task.uid
        })
        return response

@task_namespace.route("/<string:task_id>")
class Task(TasksBase):
    """Methods for a specific task."""

    @api.doc(responses={200: "OK", 400: "Unknown task id"})
    def get(self, task_id):
        """Get the task by given id."""
        task = db_model_Task.query.filter_by(id=task_id).first()

        if task is None:
            task_namespace.abort(
                404, "Wrong parameter",
                status=f"Can't find a task with the id \"{task_id}\".",
                statusCode="404")

        return jsonify(task.to_json())

    @api.doc(responses={200: "OK", 404: "Unknown task id"})
    def put(self, task_id):
        """Update the task of given id."""
        res = db_model_Task.query.filter_by(id=task_id)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Can't find a task with the id \"{task_id}\".",
                statusCode="404")

        fields = task.to_json().keys()
        for field in fields:
            if field in request.json:
                setattr(task, field, request.json[field])

        db.session.commit()

        return jsonify({
            "message": f"Task \"{task_id}\" updated."
        })

    @api.doc(responses={200: "OK", 404: "Unknown task id"})
    def delete(self, task_id):
        """Delete a task."""
        res = db_model_Task.query.filter_by(id=task_id)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Can't find a task with the id \"{task_id}\".",
                statusCode="404")

        message = f"Task \"{task.id}\" deleted."
        res.delete()
        db.session.commit()

        return jsonify({
            "message": message
        })
