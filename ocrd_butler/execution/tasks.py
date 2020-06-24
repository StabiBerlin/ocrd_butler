# -*- coding: utf-8 -*-

"""Celery tasks definitions."""

import json
import os
import subprocess
import uuid

from flask import current_app

from celery import shared_task

from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_success,
)

from ocrd.resolver import Resolver
from ocrd.processor.base import run_cli

from ocrd_butler import celery
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task



@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    current_app.logger.info("Start processing task '{0}'.", task_id)

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    current_app.logger.info("Finished processing task '{0}'.", task_id)

@task_success.connect
def task_success_handler(sender, result, **kwargs):
    task = db_model_Task.query.filter_by(id=result["task_id"]).first()
    task.status = "SUCCESS"
    task.results = result
    db.session.commit()
    current_app.logger.info("Success on task id: '{0}', worker task id: {1}.",
                            task.id, task.worker_task_id)

@task_failure.connect
def task_failure_handler(sender, result, **kwargs):
    task = db_model_Task.query.filter_by(id=result["task_id"]).first()
    task.status = "FAILURE"
    db.session.commit()
    current_app.logger.info("Failure on task id: '{0}', worker task id: {1}.",
                            task.id, task.worker_task_id)

@celery.task(bind=True)
def run_task(self, task):
    """ Create a task an run the given chain. """
    # TODO: Check if there is the active problem in olena_binarize with
    #       other basenames than mets.xml.
    # mets_basename = "{}.xml".format(task["id"])
    mets_basename = "mets.xml"

    # Create workspace
    dst_dir = "{}/{}".format(current_app.config["OCRD_BUTLER_RESULTS"],
                             task["uid"])

    resolver = Resolver()
    workspace = resolver.workspace_from_url(
        task["src"],
        dst_dir=dst_dir,
        mets_basename=mets_basename,
        clobber_mets=True
    )

    for file_name in workspace.mets.find_files(fileGrp=task["default_file_grp"]):
        if not file_name.local_filename:
            workspace.download_file(file_name)

    workspace.save_mets()

    # TODO: Steps could be saved along the other task information to get a
    # more informational task.
    for index, processor_name in enumerate(task["chain"]["processors"]):
        if index == 0:
            input_file_grp = task["default_file_grp"]
        else:
            previous_processor = PROCESSORS_ACTION[task["chain"]["processors"][index-1]]
            input_file_grp = previous_processor["output_file_grp"]

        processor = PROCESSORS_ACTION[processor_name]

        # Its possible to override the default parameters of the processor.
        kwargs = {"parameter": {}}
        if "parameters" in processor:
            kwargs["parameter"] = processor["parameters"]
        if processor_name in task["parameters"]:
            kwargs["parameter"].update(task["parameters"][processor_name])
        parameter = json.dumps(kwargs["parameter"])

        mets_url = "{}/mets.xml".format(dst_dir)
        run_cli(
            processor["executable"],
            mets_url=mets_url,
            resolver=resolver,
            workspace=workspace,
            log_level="DEBUG",
            input_file_grp=input_file_grp,
            output_file_grp=processor["output_file_grp"],
            parameter=parameter)

        # reload mets
        workspace.reload_mets()

        current_app.logger.info("Finished processing task '{0}'.", task["id"])

    return {
        "task_id": task["id"],
        "result_dir": dst_dir,
        "status": "SUCCESS"
    }
