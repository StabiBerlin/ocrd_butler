# -*- coding: utf-8 -*-

"""Testing the tasks for `ocrd_butler` package."""

from os import listdir
from os.path import isfile, join
import shutil


import pytest
from pytest import raises
from celery.exceptions import Retry

from flask_restplus import fields

from ocrd_butler.api.models import task_model
from ocrd_butler.execution.tasks import create_task

import ocrd

task_config = {
    "id": "PPN80041750X",
    "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
    "file_grp": "DEFAULT",
    "TesserocrRecognize": {
        "parameter": {
            "model": "deu"
        }
    }
}

def test_task_model():
    assert "id" in task_model
    assert "file_grp" in task_model
    assert "mets_url" in task_model
    assert "tesseract_model" in task_model

    for field in task_model:
        assert type(task_model[field]) == fields.String


@pytest.mark.celery(result_backend='redis://')
def test_create_task(mocker):
    """ Test our create_task task.
        This really creates the output.
    """
    # https://github.com/pytest-dev/pytest-mock/ # -> its not working. why? dunno yet.
    mocker.patch("ocrd.processor.base.run_processor")
    task = create_task(task_config)
    task
    # ocrd.processor.base.run_processor.assert_called()


def test_task_results(tmp_dir):
    # result_dir = join(tmp_dir, 'PPN80041750X')
    result_dir = join("/tmp/ocrd_butler_results", "PPN80041750X", "RECOGNIZE")
    shutil.rmtree(result_dir, ignore_errors=True)

    task = create_task(task_config)
    assert task == {'task_id': 'PPN80041750X', 'status': 'Created'}

    result_files = [f for f in listdir(result_dir)]
    with open(join(result_dir, result_files[1])) as result_file:
        text = result_file.read()
        assert '<pc:Unicode>Wittenberg:</pc:Unicode>' in text

def test_task_results_with_model(tmp_dir):
    # result_dir = join(tmp_dir, 'PPN80041750X')
    result_dir = join("/tmp/ocrd_butler_results", "PPN80041750X", "RECOGNIZE")
    shutil.rmtree(result_dir, ignore_errors=True)

    task_config_deu = task_config
    task_config_deu["TesserocrRecognize"]["parameter"]["model"] = "frk"

    task = create_task(task_config)
    assert task == {'task_id': 'PPN80041750X', 'status': 'Created'}

    result_files = [f for f in listdir(result_dir)]
    with open(join(result_dir, result_files[1])) as result_file:
        text = result_file.read()
        assert '<pc:Unicode>Wietenberg;</pc:Unicode>' in text
