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

class TasksBase(Resource):
    """Base methods for tasks."""

    def __init__(self, api_obj, *args, **kwargs):
        super().__init__(api_obj, *args, **kwargs)
        self.get_actions = (
            "status",
            "results",
            "download_results",
            "download_txt",
            "download_page",
            "download_alto",
            "download_alto_with_images",
            "log",
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


@task_namespace.route("/<string:task_uid>")
class Task(TasksBase):
    """Run actions on the task."""

    @api.doc(reponses={200: "Found", 404: "Unknown task"})
    def get(self, task_uid=None):
        """ Get one task.
        """
        if task_uid is not None:
            task = db_model_Task.get(uid=task_uid)
            return jsonify(task.to_json())

        task_namespace.abort(
            404, "Unknown task.",
            status=f"Unknown task for uid \"{task_uid}\".",
            statusCode="404")



@task_namespace.route("/<string:task_uid>/<string:action>")
class TaskActions(TasksBase):
    """Run actions on the task."""

    @api.doc(responses={200: "OK", 400: "Unknown action",
                        404: "Unknown task", 500: "Error"})
    def post(self, task_uid, action):
        """
        Execute the given action for the task.

        Available post actions:
        * run
        * rerun
        * stop
        * page_to_alto

        TODO: Return the actions as OPTIONS.
        """
        logger.info(f"Task {task_uid} post action {action} called.")

        task = db_model_Task.get(uid=task_uid)
        if task is None:
            task = db_model_Task.get(id=task_uid)

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Unknown task for uid \"{task_uid}\".",
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
    def get(self, task_uid, action):
        """
        Get information or results of the task.

        Available GET actions:
        * status
        * results
        * download_results
        * download_txt
        * download_page
        * download_alto
        * log

        TODO: Return the actions as OPTIONS.
        """
        logger.info(f"Task {task_uid} get action {action} called.")

        task = db_model_Task.get(uid=task_uid)
        if task is None:
            task = db_model_Task.get(id=task_uid)

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Unknown task with id or uid \"{task_uid}\".",
                statusCode="404")

        if action not in self.get_actions:
            task_namespace.abort(
                400, "Unknown action.",
                status=f"Unknown action \"{action}\".",
                statusCode="400")

        if (action.startswith("download") or action == "results")\
                and task.status != "SUCCESS":
            task_namespace.abort(
                400, "Task not ready yet.",
                status=f"Action \"{action}\" not possible.",
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
        page_to_alto_util(task.uid, task.results['result_dir'])

        return jsonify({
            "status": "SUCCESS",
            "msg": f"You can get the results via {host_url(request)}api/tasks/{task.uid}/download_alto"
        })

    def download_results(self, task):
        """ Download the results of the task as ALTO XML and include the images. """
        if 'result_dir' in task.results:
            results_path = pathlib.Path(task.results["result_dir"])
        else:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find results for task {task.uid}"
            })

        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            # zip_file.write(f"{results_path}/mets.xml", arcname="mets.xml")
            for root, dirs, files in os.walk(results_path):
                for _file in files:
                    zip_file.write(os.path.join(root, _file),
                            os.path.relpath(os.path.join(root, _file),
                                            os.path.join(results_path, '..')))
        data.seek(0)

        return send_file(
            data,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"ocr_alto_xml_{task.uid}.zip"
        )

    def download_page(self, task):
        """ Download the results of the task for e.g. pageviewer, including PAGE XML,
            METS file and DEFAULT images.
        """
        if 'result_dir' in task.results:
            page_result_path = ocr_result_path(task.results['result_dir'])
        else:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task.uid}"
            })
        if page_result_path is None:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find page results for task {task.uid}"
            })

        img_dir = os.path.join(f"{task.results['result_dir']}/{task.default_file_grp}")
        img_path = pathlib.Path(img_dir)

        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            zip_file.write(f"{task.results['result_dir']}/mets.xml", arcname="mets.xml")
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
            attachment_filename=f"ocr_page_xml_{task.uid}.zip"
        )

    def download_alto_with_images(self, task):
        """ Download the results of the task as ALTO XML and include the images. """
        if 'result_dir' in task.results:
            alto_path = alto_result_path(task.results['result_dir'])
        else:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find results for task {task.uid}"
            })
        if not os.path.exists(alto_path):
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find alto results for task {task.uid}"
            })

        img_dir = os.path.join(f"{task.results['result_dir']}/{task.default_file_grp}")
        img_path = pathlib.Path(img_dir)
        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            zip_file.write(f"{task.results['result_dir']}/mets.xml", arcname="mets.xml")
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
            attachment_filename=f"ocr_alto_xml_{task.uid}.zip"
        )

    def download_alto(self, task):
        """ Download the results of the task as ALTO XML. """
        if 'result_dir' in task.results:
            alto_path = alto_result_path(task.results['result_dir'])
        else:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find results for task {task.uid}"
            })
        if not os.path.exists(alto_path):
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find alto results for task {task.uid}"
            })

        data = io.BytesIO()
        with zipfile.ZipFile(data, mode='w') as zip_file:
            for f_name in alto_path.iterdir():
                arcname = f"{os.path.basename(f_name)}"
                zip_file.write(f_name, arcname=arcname)
        data.seek(0)

        return send_file(
            data,
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"ocr_alto_xml_{task.uid}.zip"
        )


    def download_txt(self, task):
        """ Download the results of the task as text. """
        # https://github.com/qurator-spk/dinglehopper/blob/master/qurator/dinglehopper/extracted_text.py#L95
        if 'result_dir' in task.results:
            page_result_path = ocr_result_path(task.results['result_dir'])
        else:
            return jsonify({
                "status": "ERROR",
                "msg": f"Can't find results for task {task.uid}"
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
            "attachment;filename=fulltext_%s.txt" % task.uid
        })
        return response


    def log(self, task):
        """ Get the log file of the task. """
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

@task_namespace.route("/<string:task_uid>")
class Task(TasksBase):
    """Methods for a specific task."""

    @api.doc(responses={200: "OK", 400: "Unknown task uid"})
    def get(self, task_uid):
        """Get the task by given uid."""
        task = db_model_Task.query.filter_by(uid=task_uid).first()
        if task is None:
            task_namespace.abort(
                404, "Wrong parameter",
                status=f"Can't find a task with the uid \"{task_uid}\".",
                statusCode="404")

        return jsonify(task.to_json())

    @api.doc(responses={200: "OK", 404: "Unknown task uid"})
    def put(self, task_uid):
        """Update the task of given uid."""
        res = db_model_Task.query.filter_by(uid=task_uid)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Can't find a task with the uid \"{task_uid}\".",
                statusCode="404")

        fields = task.to_json().keys()
        for field in fields:
            if field in request.json:
                setattr(task, field, request.json[field])

        db.session.commit()

        return jsonify({
            "message": f"Task \"{task_uid}\" updated."
        })

    @api.doc(responses={200: "OK", 404: "Unknown task uid"})
    def delete(self, task_uid):
        """Delete a task."""
        res = db_model_Task.query.filter_by(uid=task_uid)
        task = res.first()

        if task is None:
            task_namespace.abort(
                404, "Unknown task.",
                status=f"Can't find a task with the uid \"{task_uid}\".",
                statusCode="404")

        message = f"Task \"{task.uid}\" deleted."
        res.delete()
        db.session.commit()

        return jsonify({
            "message": message
        })
