# -*- coding: utf-8 -*-

"""Testing the tasks for `ocrd_butler` package."""

import pytest
from pytest import raises
from celery.exceptions import Retry
from unittest.mock import patch

from ocrd_butler.app import task_model
from ocrd_butler.tasks import create_task


@pytest.mark.celery(result_backend='redis://')
@patch('ocrd_butler.tasks.create_task')
def test_create_task(mock):
    """ Test our create_task task.
        This really creates the output.
    """
    task = create_task({
            "id": "PPN80041750X",
            "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
            "file_grp": "DEFAULT",
            "tesseract_model": "deu"
        })
    assert task == {'task_id': 'PPN80041750X', 'status': 'Created'}

# @pytest.mark.celery(result_backend='redis://')
# @patch('ocrd_butler.tasks.create_task') # this seems not to work
# def test_task_results(mock, tmp_dir):
#     task = create_task({
#             "id": "PPN80041750X",
#             "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
#             "file_grp": "DEFAULT",
#             "tesseract_model": "deu"
#         })

#     from os import listdir
#     from os.path import isfile, join
#     resultfiles = [f for f in listdir(tmp_dir) if join(tmp_dir, f)]
#     # TODO: use the test config for the app...
