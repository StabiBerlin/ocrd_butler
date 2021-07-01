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
from ocrd_butler.util import logger, to_json, host_url, flower_url

log = logger(__name__)

task_namespace = api.namespace("tasks", description="Manage OCR-D Tasks")

page_xml_namespaces = {
    "page_2009-03-16": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2009-03-16",
    "page_2010-01-12": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-01-12",
    "page_2010-03-19": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-03-19",
    "page_2013-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
    "page_2016-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15",
    "page_2017-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15",
    "page_2018-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15",
    "page_2019-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
}


# get the status of a task
# get the results of a task - this collect links to the resources like mets files, images, etc.
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
        log.info(f"Task {task_id} post action {action} called.")

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

        TODO: Return the actions as OPTIONS.
        """
        log.info(f"Task {task_id} get action {action} called.")

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
        # worker_task = run_task.apply_async(args=[task.to_json()],
        #                                    countdown=20)
        # worker_task = run_task(task.to_json())
        log.info("run task: %s", task)
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
        page_result_dir = self.page_result_dir(task_info)
        page_result_path = pathlib.Path(page_result_dir)
        alto_result_path = self.alto_result_path(task_info)

        if page_result_dir is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task_info['result']['task_id']}"
            })

        for file_path in page_result_path.iterdir():
            converter = OcrdPageAltoConverter(page_filename=file_path)
            alto_xml = converter.convert()
            alto_file_name = file_path.name.replace("CALAMARI", "ALTO")
            alto_result_file = alto_result_path.joinpath(alto_file_name)
            with open(alto_result_file, "w") as alto_file:
                alto_file.write(str(alto_xml))

        return jsonify({
            "status": "SUCCESS",
            "msg": f"You can get the results via {host_url(request)}api/tasks/{task.uid}/download_alto"
        })

    def page_result_dir(self, task_info: dict, path_part: str = "OCR-D-OCR") -> pathlib.Path:
        """ Get base path to the page xml results of the task. """
        result_xml_files = glob.glob(f"{task_info['result']['result_dir']}/*/*.xml")
        for file in result_xml_files:
            if not path_part in file:  # This is a bit fixed.
                continue
            tree = ET.parse(file)
            xmlns = tree.getroot().tag.split("}")[0].strip("{")
            if xmlns in page_xml_namespaces.values():
                return os.path.dirname(file)

    def alto_result_path(self, task_info: dict) -> pathlib.Path:
        """ Get path to dir for alto xml files. If it not exists, it will be created. """
        alto_path = f"{task_info['result']['result_dir']}/OCR-D-OCR-ALTO"
        if not os.path.exists(alto_path):
            os.mkdir(alto_path)
        return pathlib.Path(alto_path)

    def download_page(self, task):
        """ Download the results of the task for e.g. pageviewer, including PAGE XML,
            METS file and DEFAULT images.
        """
        task_info = task_information(task.worker_task_id)
        page_result_dir = self.page_result_dir(task_info)
        page_result_path = pathlib.Path(page_result_dir)

        if page_result_dir is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task_info['result']['task_id']}"
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
            attachment_filename=f"ocr_page_xml_{task_info['result']['task_id']}.zip"
        )

    def download_alto(self, task):
        """ Download the results of the task as ALTO XML. """
        task_info = task_information(task.worker_task_id)
        alto_xml_dir = os.path.join(task_info["result"]["result_dir"], "OCR-D-OCR-ALTO")
        if not os.path.exists(alto_xml_dir):
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find alto results for task {task_info['result']['task_id']}"
            })

        img_dir = os.path.join(f"{task_info['result']['result_dir']}/{task.default_file_grp}")
        img_path = pathlib.Path(img_dir)
        alto_path = pathlib.Path(alto_xml_dir)
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
            attachment_filename="ocr_alto_xml_%s.zip" % task_info["result"]["task_id"]
        )

    def download_txt(self, task):
        """ Download the results of the task as text. """
        # https://github.com/qurator-spk/dinglehopper/blob/master/qurator/dinglehopper/extracted_text.py#L95
        task_info = task_information(task.worker_task_id)
        page_result_dir = self.page_result_dir(task_info)
        page_result_path = pathlib.Path(page_result_dir)

        if page_result_dir is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task_info['result']['task_id']}"
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
