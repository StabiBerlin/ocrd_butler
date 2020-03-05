# -*- coding: utf-8 -*-

"""Celery tasks definitions."""

import json
import os
import subprocess
import uuid

from flask import current_app

from ocrd.resolver import Resolver
from ocrd.processor.base import run_cli

from ocrd_butler import celery

from ocrd_butler.api.processors import PROCESSORS_ACTION


@celery.task()
def create_task(task):
    """ Create a task an run the given chain. """
    processors = task["processors"]
    # TODO: Check if there is the active problem in olena_binarize with
    #       other basenames than mets.xml.
    # mets_basename = "{}.xml".format(task["id"])
    mets_basename = "mets.xml"

    # Create workspace
    dst_dir = "{}/{}-{}".format(current_app.config["OCRD_BUTLER_RESULTS"],
                                task["id"],
                                uuid.uuid1().__str__())

    resolver = Resolver()
    workspace = resolver.workspace_from_url(
        task["mets_url"],
        dst_dir=dst_dir,
        mets_basename=mets_basename,
        clobber_mets=True
    )

    for file_name in workspace.mets.find_files(fileGrp=task["file_grp"]):
        if not file_name.local_filename:
            workspace.download_file(file_name)

    workspace.save_mets()

    # TODO: Steps could be saved along the other task information to get a
    # more informational task.
    for index, processor_name in enumerate(processors):
        if index == 0:
            input_file_grp = task["file_grp"]
        else:
            previous_processor = PROCESSORS_ACTION[processors[index-1]]
            input_file_grp = previous_processor["output_file_grp"]

        processor = PROCESSORS_ACTION[processor_name]

        # Its possible to override the default parameters of the processor.
        kwargs = {"parameter": {}}
        if "parameters" in processor:
            kwargs["parameter"] = processor["parameters"]
        if "parameter" in task and processor_name in task["parameter"]:
            kwargs["parameter"].update(task["parameter"][processor_name])
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

        current_app.logger.info("Finished processing task '%s'", task)

    return {
        "task_id": task["id"],
        "result_dir": dst_dir,
        "status": "Created"
    }
