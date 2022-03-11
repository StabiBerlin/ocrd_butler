# -*- coding: utf-8 -*-

"""Celery tasks definitions."""
from __future__ import print_function

import json
from logging import Logger
from pathlib import (
    Path,
    PurePosixPath
)
from urllib.parse import (
    urlparse,
    unquote
)
import sys

from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_success,
)

from flask import current_app

from ocrd_models import OcrdFile
from ocrd.resolver import Resolver
from ocrd.processor.base import run_cli
from ocrd.workspace import Workspace
from ocrd_utils import getLogger

from ocrd_butler import celery
from ocrd_butler.database import db
from ocrd_butler.database.models import Task as db_model_Task
from ocrd_butler.util import (
    logger,
    ocr_result_path
)


def get_task_backend_state(task_id: str) -> str:
    """ Get the current state of the task from the celery backend.
        Currently not used.
    """
    return celery.backend.get_status(task_id)


def update_task(uid: str, state: str, results: dict =None):
    """ Update the given state of the task in our database.
        Also set the results if given.
    """
    try:
        from ocrd_butler.app import flask_app
        with flask_app.app_context():
            task = db_model_Task.get(uid=uid)
            task.status = state
            if results is not None:
                task.results = results
            db.session.commit()
    except Exception as exc:
        caller = sys._getframe().f_back.f_code.co_name
        logger.error(f"{caller} -> Can't set status for "
                     f"task: {uid}; exc: {exc}")


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    logger.debug(f"task_prerun_handler -> task: {task_id}, task: {task}, "
                 f"args: {args}, kwargs: {kwargs}")
    uid = kwargs.get('args')[0].get('uid')
    update_task(uid, 'STARTED')
    logger.info(f"Start processing task {uid}.")


@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, *args, **kwargs):
    logger.debug(f"task_postrun_handler -> task: {task_id}, task: {task}, "
                 f"args: {args}, kwargs: {kwargs}")
    uid = kwargs.get('args')[-1].get('uid')
    update_task(uid, state)
    logger.info(f"Finished processing task {uid}.")


@task_success.connect
def task_success_handler(result, *args, **kwargs):
    logger.debug(f"task_success_handler -> result: {result}, "
                 f"args: {args}, kwargs: {kwargs}")
    uid = result.get('uid')
    update_task(uid, 'SUCCESS', result)
    logger.info(f"Success on task {uid} with a result of {result}.")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo, *args, **kwargs):
    logger.debug(
        f"task_failure_handler -> task: {task_id}, exception: {exception}, "
        f"traceback: {traceback}, einfo: {einfo}, args: {args}, "
        f"kwargs: {kwargs}"
    )
    uid = kwargs.get('args')[0].get('uid')
    update_task(uid, 'FAILURE')
    logger.error(f"Task {task_id} failed, "
                 f"exception: {exception}, traceback: {traceback}.")


def add_max_file_to_workspace(workspace: Workspace, file_name: OcrdFile) -> OcrdFile:
    """ Use a remote TIFF representation instead of JPG of a given workspace file,
    and add the corresponding file entry to the workspace.
    """
    iiif_max_url = file_name.url.replace('.jpg', '.tif')
    file_id = file_name.ID.replace("DEFAULT", "MAX")
    return workspace.add_file(
        file_grp="MAX",
        pageId=file_name.pageId,
        url=iiif_max_url,
        ID=file_id,
        mimetype="image/tiff",
        extension=".tif"
    )


def prepare_workspace(task: dict, resolver: Resolver, dst_dir: str) -> Workspace:
    """Prepare a workspace and return it."""
    mets_basename = "mets.xml"

    workspace = resolver.workspace_from_url(
        task["src"],
        dst_dir=dst_dir,
        mets_basename=mets_basename,
        clobber_mets=True
    )

    if task[
        "default_file_grp"
    ] == "MAX" and "MAX" not in workspace.mets.file_groups:
        for file_name in workspace.mets.find_files(
                fileGrp="DEFAULT"
        ):
            workspace.download_file(
                add_max_file_to_workspace(
                    workspace, file_name
                )
            )
    else:
        for file_name in workspace.mets.find_files(
                fileGrp=task["default_file_grp"]
        ):
            if not file_name.local_filename:
                workspace.download_file(file_name)

    workspace.save_mets()

    return workspace


def determine_input_file_grp(
    task: dict, processor: dict, previous_processor: dict
) -> str:
    """ determine ``input_file_grp`` to be used for given processor, based
    on its own configuration, the previous processor's ``output_file_grp``,
    or the task's ``default_file_grp`` parameter, respectively.

    >>> task = {'default_file_grp': 'MAX'}
    >>> prev = {'output_file_grp': 'OCR-D-IMG-BIN'}
    >>> proc = {'input_file_grp': 'OCR-D-IMG-FOO'}

    >>> determine_input_file_grp(task, proc, prev)
    'OCR-D-IMG-FOO'

    >>> determine_input_file_grp(task, {}, prev)
    'OCR-D-IMG-BIN'

    >>> determine_input_file_grp(task, {}, {})
    'MAX'

    """
    return processor.get(
        'input_file_grp',
        (
            previous_processor or {}
        ).get(
            'output_file_grp',
            task['default_file_grp']
        )
    )


def to_task_log(
    task_log_handler:Logger, log_file:str, logger_path:str, task:dict):
    """ Write the information from the celery service file to the task log. """
    logger.remove(task_log_handler)
    task_log_handler = logger.add(log_file, format='{message}', mode='a')
    service_debug_log = f"{logger_path}/celery/ocrd-butler.celery.service.stderr.log"
    if Path(service_debug_log).is_file():
        lines = []
        start = f'Start processing task {task["uid"]}'
        end = f'Finished processing task {task["uid"]}'
        record = False
        with open(service_debug_log, 'r') as log:
            for line in log:
                if start in line:
                    record = True
                if end in line:
                    break
                if record:
                    lines.append(line.rstrip())
        for line in lines:
            logger.info(line)
    logger.remove(task_log_handler)


@celery.task(bind=True)
def run_task(self, task: dict) -> dict:
    """ Create a task an run the given workflow. """
    logger_path = current_app.config["LOGGER_PATH"]
    log_file = f"{logger_path}/task-{task['uid']}.log"
    task_log_handler = logger.add(log_file)

    logger.info(f'Start processing task {task["uid"]}.')

    # Create workspace
    from ocrd_butler.app import flask_app
    with flask_app.app_context():
        dst_dir = "{}/{}".format(
            current_app.config["OCRD_BUTLER_RESULTS"], task["uid"]
        )
        resolver = Resolver()
        workspace = prepare_workspace(task, resolver, dst_dir)
        logger.info(f"Prepare workspace for task '{task['uid']}'.")

    task_processors = task["workflow"]["processors"]
    mets_url = "{}/mets.xml".format(dst_dir)

    # TODO: Steps could be saved along the other task information to get a
    # more informational task.
    previous_processor = None

    for processor in task_processors:
        input_file_grp = determine_input_file_grp(
            task, processor, previous_processor
        )
        previous_processor = processor

        # Its possible to override the parameters of the processor in the task.
        kwargs = {"parameter": {}}
        if "parameters" in processor:
            kwargs["parameter"].update(processor["parameters"])
        if processor["name"] in task["parameters"]:
            kwargs["parameter"].update(task["parameters"][processor["name"]])
        parameter = json.dumps(kwargs["parameter"])

        logger.info(f'Start processor {processor["name"]}. {json.dumps(processor)}.')

        logger.info(f'Run processor {processor["name"]}.')
        exit_code = run_cli(
            processor["executable"],
            mets_url=mets_url,
            resolver=resolver,
            workspace=workspace,
            log_level="DEBUG",
            input_file_grp=input_file_grp,
            output_file_grp=processor["output_file_grp"],
            parameter=parameter,
        )

        if exit_code != 0:
            logger.info(f'Finished processing task {task["uid"]}.')
            to_task_log(task_log_handler, log_file, logger_path, task)
            raise Exception(f"Processor {processor['name']} failed with exit code {exit_code}.")

        workspace.reload_mets()
        logger.info(f'Finished processor {processor["name"]} for task {task["uid"]}.')

    logger.info(f'Finished processing task {task["uid"]}.')
    to_task_log(task_log_handler, log_file, logger_path, task)

    return {
        "id": task["id"],
        "uid": task["uid"],
        "result_dir": dst_dir
    }
