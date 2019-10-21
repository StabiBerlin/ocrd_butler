# -*- coding: utf-8 -*-

"""Main module."""

import json
import os
import sys
import subprocess
import time

from flask import Flask, request, jsonify
from flask_restplus import Api, Resource, fields

from ocrd_butler.celery_utils import create_celery_app


flask_app = Flask(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
config_file_path = os.path.join(dir_path, "./config/config.json")
config_file = os.path.abspath(config_file_path)
try:
    with open(config_file) as config_handle:
        config_json = json.load(config_handle)
        flask_app.config.update(config_json)
        if not os.path.exists(flask_app.config["OCRD_BUTLER_RESULTS"]):
            os.makedirs(flask_app.config["OCRD_BUTLER_RESULTS"])
except FileNotFoundError as exc:
    print ("Can't find configuration file '{}'. ({})".format(
        config_file,
        exc.__str__()))

# celery configuration
flask_app.config.update(
    CELERY_RESULT_BACKEND_URL="redis://localhost:6379",
    CELERY_BROKER_URL="redis://localhost:6379"
)
celery = create_celery_app(flask_app)

@celery.task()
def create_task(task):
    # maybe create a unique id for a task?


    # Create workspace
    from ocrd.cli.workspace import WorkspaceCtx, workspace_clone
    dst_dir = "{}/{}".format(flask_app.config["OCRD_BUTLER_RESULTS"], task["id"])
    ctx = WorkspaceCtx(
        directory = dst_dir,
        mets_basename = "{}.xml".format(task["id"]),
        automatic_backup = True
    )
    workspace = ctx.resolver.workspace_from_url(
        task["mets_url"],
        dst_dir=dst_dir,
        mets_basename=ctx.mets_basename,
        clobber_mets=True
    )

    for f in workspace.mets.find_files(fileGrp=task["file_grp"]):
        if not f.local_filename:
            workspace.download_file(f)

    workspace.save_mets()


    from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
    from ocrd_tesserocr.segment_line import TesserocrSegmentLine
    from ocrd_tesserocr.segment_word import TesserocrSegmentWord
    from ocrd_tesserocr.recognize import TesserocrRecognize
    from ocrd.processor.base import run_processor

    run_processor(TesserocrSegmentRegion,
                  mets_url=task['mets_url'],
                  workspace=workspace,
                  input_file_grp="DEFAULT",
                  output_file_grp="SEGMENTREGION")
    run_processor(TesserocrSegmentLine,
                  mets_url=task['mets_url'],
                  workspace=workspace,
                  input_file_grp="SEGMENTREGION",
                  output_file_grp="SEGMENTLINE")
    run_processor(TesserocrSegmentWord,
                  mets_url=task['mets_url'],
                  workspace=workspace,
                  input_file_grp="SEGMENTLINE",
                  output_file_grp="SEGMENTWORD")
    # TODO: model has to be stored in a json file with the needed parameters
    run_processor(TesserocrRecognize,
                  mets_url=task['mets_url'],
                  workspace=workspace,
                  input_file_grp="SEGMENTWORD",
                  output_file_grp="RECOGNIZE",
                  parameter={
                      "model": task['tesseract_model'],
                      "overwrite_words": False,
                      "textequiv_level": "line"
                    })

    return {
        "task_id": task["id"],
        "status": "Created"
    }

# flask-restplus configuration
app = Api(
    app = flask_app,
    version="v1",
    title="ORC-D Tasks",
    description="OCR-D Tasks API")

name_space = app.namespace(
    "ocrd-tasks",
    description="Manage OCR-D Tasks")

task_model = app.model("Task Model",
            {
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

        return {
            "task_id": worker_task.id,
            "state": worker_task.state,
            # 'current': worker_task.info.get('current', 0),
            # 'total': worker_task.info.get('total', 1),
            # 'status': worker_task.info.get('status', '')
        }

