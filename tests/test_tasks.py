# -*- coding: utf-8 -*-

"""Testing the tasks for `ocrd_butler` package."""

import glob
import os
import shutil

import pytest
from pytest import raises
from flask_testing import TestCase

from celery.exceptions import Retry

from flask_restx import fields

from ocrd_butler.api.models import task_model
from ocrd_butler.execution.tasks import run_task
from ocrd_butler.factory import create_app
from ocrd_butler.database import db
from ocrd_butler.config import TestingConfig


CURRENT_DIR = os.path.dirname(__file__)

task_tesseract_config = {
    "id": "PPN80041750X",
    "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
    "file_grp": "DEFAULT",
    # "chain": "Tesseract One",
    "processors": [
        "ocrd-tesserocr-segment-region",
        "ocrd-tesserocr-segment-line",
        "ocrd-tesserocr-segment-word",
        "ocrd-tesserocr-recognize"
    ],
    "parameter": {
        "ocrd-tesserocr-recognize": {
            "model": "deu"
        }
    }
}

task_tesseract_with_calamari_rec_config = {
    "id": "PPN80041750X",
    "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
    "file_grp": "DEFAULT",
    "processors": [
        "ocrd-tesserocr-segment-region",
        "ocrd-tesserocr-segment-line",
        "ocrd-tesserocr-segment-word",
        "ocrd-calamari-recognize"
    ],
    "parameter": {
        "ocrd-calamari-recognize": {
            "checkpoint": "{0}/calamari_models/*ckpt.json".format(CURRENT_DIR)
        }
    }
}

task_olena_bin_calamari_rec_config = {
    "id": "PPN80041750X",
    "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
    "file_grp": "DEFAULT",
    "processors": [
        "ocrd-olena-binarize",
        "ocrd-tesserocr-segment-region",
        "ocrd-tesserocr-segment-line",
        "ocrd-calamari-recognize"
    ],
    "parameter": {
        "ocrd-olena-binarize": {
            "impl": "sauvola-ms-split"
        },
        "ocrd-calamari-recognize": {
            "checkpoint": "{0}/calamari_models/*ckpt.json".format(CURRENT_DIR)
        }
    }
}


class TasksTestExecution(TestCase):
    """ tbd. """

    def create_app(self):
        app = create_app(config=TestingConfig)
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def clearTestDir(self):
        config = TestingConfig()
        test_dirs = glob.glob("%s/*" % config.OCRD_BUTLER_RESULTS)
        for test_dir in test_dirs:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_task_model(self):
        assert "works_id" in task_model # TODO: should be work_id
        assert "file_grp" in task_model
        assert "mets_url" in task_model
        assert "chain" in task_model
        assert "parameter" in task_model

        for field in task_model:
            assert isinstance(task_model[field], fields.String)

    @pytest.mark.celery(result_backend='redis://')
    def test_run_task(self):
        """ Test our run_task task.
            This really creates the output.
        """
        # https://github.com/pytest-dev/pytest-mock/ # -> its not working. why? dunno yet.
        # mocker.patch("ocrd.processor.base.run_processor")
        # ocrd.processor.base.run_processor.assert_called()

    def test_task_results_deu(self):
        task = run_task(task_tesseract_config)

        assert task["task_id"] == "PPN80041750X"
        assert task["status"] == "Created"
        assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/PPN80041750X")

        ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-TESS")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[1])) as result_file:
            text = result_file.read()
            assert '<Label value="word" type="textequiv_level"/>' in text
            assert "<Unicode>Wittenberg:</Unicode>" in text

        # self.clearTestDir()

    def test_task_results_frk(self):
        task_config_frk = task_tesseract_config
        task_config_frk["parameter"]["ocrd-tesserocr-recognize"]["model"] = "frk"

        task = run_task(task_config_frk)
        assert task["task_id"] == "PPN80041750X"
        assert task["status"] == "Created"
        assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/PPN80041750X")

        ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-TESS")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[1])) as result_file:
            text = result_file.read()
            assert "<Unicode>Wittenberg:</Unicode>" in text

    def test_task_results_cal(self):
        """TODO: Currently no results, using /opt/calamari_models/fraktur_historical/0.ckpt.json
           as checkpoint file.
        """
        task_config_cal = task_tesseract_with_calamari_rec_config

        task = run_task(task_config_cal)
        assert task["task_id"] == "PPN80041750X"
        assert task["status"] == "Created"
        assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/PPN80041750X")

        ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[1])) as result_file:
            text = result_file.read()
            assert "<Unicode>iieeers</Unicode>" in text

    def test_task_results_ole_cal(self):
        """TODO: Currently no results, using /opt/calamari_models/fraktur_historical/0.ckpt.json
           as checkpoint file.
        """
        task_config_cal = task_olena_bin_calamari_rec_config

        task = run_task(task_config_cal)
        assert task["task_id"] == "PPN80041750X"
        assert task["status"] == "Created"
        assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/PPN80041750X")

        ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[1])) as result_file:
            text = result_file.read()
            assert "<Unicode>Wittenberg:</Unicode>" in text
