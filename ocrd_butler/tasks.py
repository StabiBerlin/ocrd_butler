# -*- coding: utf-8 -*-

"""Celery tasks definitions."""

from flask import current_app
import os
import subprocess

from ocrd.cli.workspace import WorkspaceCtx, workspace_clone

from ocrd.processor.base import run_processor

from ocrd_butler import celery
from ocrd_butler.util import get_config_json

from ocrd_butler.chains import chain_config, tesserocr_chain

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

    # steps could be saved along the other task information to get a more informational task

    for index, step in enumerate(tesserocr_chain):
        input_file_grp = "DEFAULT"
        if index > 0:
            input_file_grp = chain_config[tesserocr_chain[index-1]["processor"]]["output_file_grp"]

        processor = chain_config[tesserocr_chain[index]["processor"]]

        if 'parameters' in step:
            for key, value in step["parameters"].items():
                if type(value) is str and value.startswith("task_"):
                    step["parameters"][key] = task[value[5:]]

        run_processor(processor["class"],
                    mets_url=task["mets_url"],
                    workspace=workspace,
                    input_file_grp=input_file_grp,
                    output_file_grp=processor["output_file_grp"])


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
                "task_id": task["id"],
                "status": "error",
                "error": exc.__str__()
            }

@celery.task()
def init_ocrd_workspace_process(task):
    init_workspace = "{} workspace -d {} find --file-grp {} --download".format(
                        ocrd_tool,
                        task["id"],
                        task["file_grp"])

    flask_app = current_app # ???

    try:
        output = subprocess.check_output([init_workspace], shell=True, cwd=flask_app.config["OCRD_BUTLER_RESULTS"])
    except subprocess.CalledProcessError as exc:
        return {
            "task_id": task["id"],
            "status": "error",
            "error": exc.__str__()
        }
