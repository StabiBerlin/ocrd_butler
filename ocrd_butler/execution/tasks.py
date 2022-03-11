# -*- coding: utf-8 -*-

"""Celery tasks definitions."""
from __future__ import print_function

import json
from pathlib import (
    PurePosixPath
)
from urllib.parse import (
    urlparse,
    unquote
)
import sys
import subprocess

from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_success,
)

from flask import current_app

from ocrd.resolver import Resolver
from ocrd.workspace import Workspace

from ocrd_butler import celery
from ocrd_butler.database import db
from ocrd_butler.database.models import Task as db_model_Task
from ocrd_butler.util import (
    logger,
)


def get_task_backend_state(task_id: str) -> str:
    """ Get the current state of the task from the celery backend.
        Currently not used.
    """
    return celery.backend.get_status(task_id)


def update_task(uid: str, state: str, results: dict = None):
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


def prepare_workspace(task: dict, resolver: Resolver, dst_dir: str) -> Workspace:
    """Prepare a workspace and return it."""
    mets_basename = "mets.xml"

    workspace = resolver.workspace_from_url(
        task["src"],
        dst_dir=dst_dir,
        mets_basename=mets_basename,
        clobber_mets=True
    )

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

    >>> task = {'default_file_grp': 'DEFAULT'}
    >>> prev = {'output_file_grp': 'OCR-D-IMG-BIN'}
    >>> proc = {'input_file_grp': 'OCR-D-IMG-FOO'}

    >>> determine_input_file_grp(task, proc, prev)
    'OCR-D-IMG-FOO'

    >>> determine_input_file_grp(task, {}, prev)
    'OCR-D-IMG-BIN'

    >>> determine_input_file_grp(task, {}, {})
    'DEFAULT'

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


def _run_processor(
    executable: str, mets_url: str, resolver: Resolver, workspace: Workspace,
    log_level: str, input_file_grp: str, output_file_grp: str, parameter: dict,
) -> subprocess.CompletedProcess:
    """ run an OCRD processor executable with the specified configuration, wait for the
    execution to complete, and return a :class:`subprocess.CompletedProcess` object.

    Basically the only difference from ``ocrd.processor.helper.run_cli`` is that
    ``/dev/stderr`` is being redirected to ``/dev/stdout``, and ``/dev/stdout`` output
    of the spawned subprocess is being captured and copied to the current logger.

    """
    args = [
        executable, '--working-dir', workspace.directory,
        '--mets', mets_url, '--log-level', log_level,
        '--input-file-grp', input_file_grp,
        '--output-file-grp', output_file_grp,
    ]
    if parameter:
        args += ['--parameter', parameter]
    logger.info(f'Start processor subprocess: `{" ".join(args)}`')
    result = subprocess.run(
        args, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    logger.info(f'Processor subprocess completed: `{" ".join(result.args)}')
    for processor_stdout_line in result.stdout.decode().split('\n'):
        logger.info(processor_stdout_line)
    logger.info(f'Processor subprocess returned with exit code {result.returncode}')
    return result


@celery.task(bind=True)
def run_task(self, task: dict) -> dict:
    """ Create a task an run the given workflow. """
    logger_path = current_app.config["LOGGER_PATH"]
    log_file = f"{logger_path}/task-{task['uid']}.log"
    task_log_handler = logger.add(log_file, format='{message}')

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

        logger.info(f'Run processor {processor["name"]} on METS file {mets_url}.')
        result = _run_processor(
            processor["executable"],
            mets_url=mets_url,
            resolver=resolver,
            workspace=workspace,
            log_level="DEBUG",
            input_file_grp=input_file_grp,
            output_file_grp=processor["output_file_grp"],
            parameter=parameter,
        )

        if result.returncode != 0:
            logger.info(f'Finished processing task {task["uid"]}.')
            raise Exception(
                f"Processor {processor['name']} failed with exit code {result.returncode}."
            )

        workspace.reload_mets()
        logger.info(f'Finished processor {processor["name"]} for task {task["uid"]}.')

    logger.info(f'Finished processing task {task["uid"]}.')
    logger.remove(task_log_handler)

    return {
        "id": task["id"],
        "uid": task["uid"],
        "result_dir": dst_dir
    }
