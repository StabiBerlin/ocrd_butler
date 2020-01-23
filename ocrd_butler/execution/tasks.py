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
from ocrd_butler.api.chains import default_chain
from ocrd_butler.api.chains import processor_chains


@celery.task()
def create_task(task):
    """ Create a task an run the given chain. """
    processors = task["processors"]

    # Create workspace
    dst_dir = "{}/{}-{}".format(current_app.config["OCRD_BUTLER_RESULTS"],
                                task["id"],
                                uuid.uuid1().__str__())

    resolver = Resolver()
    workspace = resolver.workspace_from_url(
        task["mets_url"],
        dst_dir=dst_dir,
        mets_basename="{}.xml".format(task["id"]),
        clobber_mets=True
    )

    for file_name in workspace.mets.find_files(fileGrp=task["file_grp"]):
        if not file_name.local_filename:
            workspace.download_file(file_name)

    workspace.save_mets()

    ocrd_tasks = []

    # steps could be saved along the other task information to get a more informational task
    for index, processor_name in enumerate(processors):
        if index == 0:
            input_file_grp = task["file_grp"]
        else:
            previous_processor = PROCESSORS_ACTION[processors[index-1]]
            input_file_grp = previous_processor["output_file_grp"]

        processor = PROCESSORS_ACTION[processor_name]

        # Its possible to override the default parameters of the processor.
        kwargs = {}
        parameter = ""
        if "parameters" in processor:
            kwargs["parameter"] = {}
            for key, value in processor["parameters"].items():
                if "parameters" in task and processor_name in task["parameters"] and\
                    key in task["parameters"][processor_name]:
                    kwargs["parameter"][key] = task["parameters"][processor_name][key]
                else:
                    kwargs["parameter"][key] = value
            # parameter = ', '.join("{!s}={!r}".format(key,val) for (key,val) in kwargs["parameter"].items())
            # kwargs["parameter"]["clobber_mets"] = True
            parameter = json.dumps(kwargs["parameter"])

        ret = run_cli(processor["executable"],
                mets_url=task["mets_url"],
                resolver=resolver,
                workspace=workspace,
                log_level="DEBUG",
                input_file_grp=input_file_grp,
                output_file_grp=processor["output_file_grp"],
                parameter=parameter)

        # returncode = run_cli(
        #     task.executable,
        #     mets,
        #     resolver,
        #     workspace,
        #     log_level=log_level,
        #     page_id=page_id,
        #     input_file_grp=','.join(task.input_file_grps),
        #     output_file_grp=','.join(task.output_file_grps),
        #     parameter=task.parameter_path
        # )

        # reload mets
        workspace.reload_mets()

        # ocrd_task = "{0} -I {1} -O {2}".format(
        #     processor["executable"][5:],
        #     input_file_grp,
        #     processor["output_file_grp"]
        # )
        # ocrd_tasks.append(ocrd_task)
        current_app.logger.info("Finished processing task '%s'", task)

    # tasks_arg = " ".join('"{0}"'.format(ocrd_t) for ocrd_t in ocrd_tasks)
    # run_tasks(task["mets_url"], "DEBUG", "PHYS_0001,PHYS_0002", ocrd_tasks)

    return {
        "task_id": task["id"],
        "result_dir": dst_dir,
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
                "status": "Error",
                "error": exc.__str__()
            }

    return {
        "task_id": task["id"],
        "status": "Created",
        "output": str(output)
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

    return {
        "task_id": task["id"],
        "status": "Created",
        "output": str(output)
    }
