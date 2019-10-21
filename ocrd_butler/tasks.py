# -*- coding: utf-8 -*-

"""Celery tasks definitions."""

from flask import current_app
import os
import subprocess

from ocrd.cli.workspace import WorkspaceCtx, workspace_clone

from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
from ocrd_tesserocr.segment_line import TesserocrSegmentLine
from ocrd_tesserocr.segment_word import TesserocrSegmentWord
from ocrd_tesserocr.recognize import TesserocrRecognize
from ocrd.processor.base import run_processor

from ocrd_butler import celery
from ocrd_butler.util import get_config_json

config_json = get_config_json()

@celery.task()
def create_task(task):
    # Create workspace
    dst_dir = "{}/{}".format(config_json["OCRD_BUTLER_RESULTS"], task["id"])
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

    # Run predefined processors.
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


## OLD task handling with subprocess
@celery.task()
def create_ocrd_workspace_process(task):

    flask_app = current_app # ???

    ocrd_tool = os.path.join(flask_app.config["OCRD_BIN"], "ocrd")
    clone_workspace = "{} workspace clone {} {}".format(
                        ocrd_tool,
                        task["mets_url"],
                        task["id"])
    output = None

    if not os.path.exists(os.path.join(flask_app.config["OCRD_BUTLER_RESULTS"], task["id"])):
        try:
            output = subprocess.check_output([clone_workspace], shell=True, cwd=flask_app.config["OCRD_BUTLER_RESULTS"])
        except subprocess.CalledProcessError as exc:
            return {
                "task_id": task['id'],
                "status": "error",
                "error": exc.__str__()
            }

@celery.task()
def init_ocrd_workspace_process(task):
    init_workspace = '{} workspace -d {} find --file-grp {} --download'.format(
                        ocrd_tool,
                        task['id'],
                        task['file_grp'])

    flask_app = current_app # ???

    try:
        output = subprocess.check_output([init_workspace], shell=True, cwd=flask_app.config["OCRD_BUTLER_RESULTS"])
    except subprocess.CalledProcessError as exc:
        return {
            "task_id": task['id'],
            "status": "error",
            "error": exc.__str__()
        }
