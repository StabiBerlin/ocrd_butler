# -*- coding: utf-8 -*-

"""Testing the tasks for `ocrd_butler` package."""

import glob
import os
import shutil

from flask_testing import TestCase
from flask_restx import fields

from ocrd_butler.api.models import task_model
from ocrd_butler.factory import create_app
from ocrd_butler.database import db
from ocrd_butler.config import TestingConfig


CURRENT_DIR = os.path.dirname(__file__)


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

    # @pytest.mark.celery(result_backend='redis://')
    # def test_run_task(self):
    #     """ Test our run_task task.
    #         This really creates the output.
    #     """
    #     # https://github.com/pytest-dev/pytest-mock/ # -> its not working. why? dunno yet.
    #     # mocker.patch("ocrd.processor.base.run_processor")
    #     # ocrd.processor.base.run_processor.assert_called()

    # def test_task_results_deu(self):
    #     task = run_task(task_tesseract_config)

    #     assert task["task_id"] == "PPN80041750X"
    #     assert task["status"] == "SUCCESS"
    #     assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/foobar123")

    #     ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-TESS")
    #     result_files = os.listdir(ocr_results)
    #     with open(os.path.join(ocr_results, result_files[1])) as result_file:
    #         text = result_file.read()
    #         assert '<pc:Label value="word" type="textequiv_level"/>' in text
    #         assert "<pc:Unicode>Wittenberg:</pc:Unicode>" in text

    #     # self.clearTestDir()

    # def test_task_results_frk(self):
    #     task_config_frk = task_tesseract_config
    #     task_config_frk["parameters"]["ocrd-tesserocr-recognize"]["model"] = "frk"

    #     task = run_task(task_config_frk)
    #     assert task["task_id"] == "PPN80041750X"
    #     assert task["status"] == "SUCCESS"
    #     assert task["result_dir"].startswith("/tmp/ocrd_butler_results_testing/foobar123")

    #     ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-TESS")
    #     result_files = os.listdir(ocr_results)
    #     with open(os.path.join(ocr_results, result_files[1])) as result_file:
    #         text = result_file.read()
    #         assert "<pc:Unicode>Wittenberg:</pc:Unicode>" in text
