# -*- coding: utf-8 -*-

"""Celery tasks definitions."""

import json
from pathlib import PurePosixPath
from urllib.parse import (
    urlparse,
    unquote
)

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

from ocrd_butler import celery
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.database import (
    db,
    models,
)
from ocrd_butler.database.models import Task as db_model_Task
from ocrd_butler.util import logger

log = logger(__name__)


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    current_app.logger.info("Start processing task '%s'.", task_id)


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    current_app.logger.info("Finished processing task '%s'.", task_id)


@task_success.connect
def task_success_handler(sender, result, **kwargs):
    task = db_model_Task.query.filter_by(id=result["task_id"]).first()
    task.status = "SUCCESS"
    task.results = result
    db.session.commit()
    current_app.logger.info("Success on task id: '%s', worker task id: %s.",
                            task.id, task.worker_task_id)


@task_failure.connect
def task_failure_handler(sender, result, **kwargs):
    log.error(f'handle task failure. sender={sender}, result={result}.')
    task = db_model_Task.query.filter_by(id=result["task_id"]).first()
    task.status = "FAILURE"
    db.session.commit()
    current_app.logger.info("Failure on task id: '%s', worker task id: %s.",
                            task.id, task.worker_task_id)


def add_max_file_to_workspace(workspace: Workspace, file_name: OcrdFile) -> OcrdFile:
    """ Uses the :const:`~.ocrd_butler.config.Config.SBB_IIIF_FULL_TIF_URL` URL template
    to locate a remote TIFF representation of a given workspace file, and add the
    corresponding file entry to the workspace.
    """
    url_path = PurePosixPath(unquote(urlparse(file_name.url).path))
    ppn = url_path.parts[2]
    img_nr = url_path.parts[5].split(".")[0]
    iiif_max_url = current_app.config["SBB_IIIF_FULL_TIF_URL"].format(ppn, img_nr)
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

    parsed_url = urlparse(task["src"])
    is_sbb = parsed_url.hostname == current_app.config["SBB_CONTENT_SERVER_HOST"]

    if is_sbb and task[
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


@celery.task(bind=True)
def run_task(self, task: models.Task) -> dict:
    """ Create a task an run the given workflow. """

    # Create workspace
    dst_dir = "{}/{}".format(current_app.config["OCRD_BUTLER_RESULTS"],
                             task["uid"])
    resolver = Resolver()
    workspace = prepare_workspace(task, resolver, dst_dir)
    task_processors = task["workflow"]["processors"]

    # TODO: Steps could be saved along the other task information to get a
    # more informational task.
    previous_processor = None

    for processor_name, processor in task_processors.items():
        if previous_processor is None:
            input_file_grp = task["default_file_grp"]
        else:
            input_file_grp = previous_processor["output_file_grp"]
        previous_processor = processor

        processor = PROCESSORS_ACTION[processor_name]

        # Its possible to override the parameters of the processor in the task.
        kwargs = {"parameter": {}}
        if processor_name in task["workflow"]["processors"]:
            kwargs["parameter"].update(task["workflow"]["processors"][processor_name])
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

        current_app.logger.info("Finished processing task '%s'.", task["id"])

    return {
        "task_id": task["id"],
        "result_dir": dst_dir,
        "status": "SUCCESS"
    }
