# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import pytest
import os
import glob
import responses
import shutil
from unittest import mock

from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db

from . import require_ocrd_processors


CURRENT_DIR = os.path.dirname(__file__)


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'amqp://',
        'result_backend': 'redis://'
    }


@pytest.fixture(scope='session')
def celery_enable_logging():
    return True


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'ocrd_butler.execution.tasks',
        # 'proj.tests.celery_signal_handlers',
    ]


# https://medium.com/@scythargon/how-to-use-celery-pytest-fixtures-for-celery-intergration-testing-6d61c91775d9
# # @pytest.mark.usefixtures("config")
# @pytest.mark.usefixtures('celery_session_app')
# @pytest.mark.usefixtures('celery_session_worker')
class ApiTaskActionRunTests(TestCase):
    """Test our api actions."""

    def setUp(self):

        from ocrd_butler import celery
        celery.conf.task_always_eager = True

        db.create_all()

        testfiles = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "files")

        with open(
                os.path.join(testfiles, "sbb-mets-PPN821929127.xml"),
                "r", encoding="utf-8"
        ) as tfh:
            responses.add(
                method=responses.GET,
                url="http://foo.bar/mets.xml",
                body=tfh.read(),
                status=200
            )

        for i in "123":
            with open(
                    os.path.join(testfiles, f"0000000{i}.jpg"), "rb"
            ) as tfh:
                img_file = tfh.read()
                responses.add(
                    method=responses.GET,
                    url=(
                        "http://content.staatsbibliothek-berlin.de/dms/"
                        f"PPN821929127/800/0/0000000{i}.jpg"
                    ),
                    body=img_file,
                    status=200,
                    content_type="image/jpg"
                )
                responses.add(
                    method=responses.GET,
                    url=(
                        "https://content.staatsbibliothek-berlin.de/dc/"
                        f"PPN821929127-0000000{i}/full/full/0/default.tif"
                    ),
                    body=img_file,
                    status=200,
                    content_type="image/tiff"
                )

    def tearDown(self):
        """Remove the test database."""
        db.session.remove()
        db.drop_all()
        # self.clearTestDir()

    def clearTestDir(self, config):
        config = TestingConfig()
        test_dirs = glob.glob(f"{config.OCRD_BUTLER_RESULTS}/*")
        for test_dir in test_dirs:
            shutil.rmtree(test_dir, ignore_errors=True)

    def create_app(self):
        return create_app(config=TestingConfig)

    def t_workflow(self):
        """Creates a workflow with tesseract processors."""
        response = self.client.post("/api/workflows", json=dict(
            name="T Workflow",
            description="Some foobar workflow.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-tesserocr-recognize",
            ],
            parameters={
                "ocrd-tesserocr-recognize": {
                    "model": "deu"
                }
            }
        ))
        return response.json["id"]

    def empty_workflow(self):
        """Creates a workflow without processors."""
        response = self.client.post("/api/workflows", json=dict(
            name="Empty Workflow",
            description="Empty but not useless workflow.",
            processors=[],
            parameters={}
        ))
        return response.json["id"]

    @responses.activate
    def test_task_max_file_download(self):
        """Check if the workspace is created."""
        self.client.post("/api/tasks", json=dict(
            workflow_id=self.empty_workflow(),
            src="http://foo.bar/mets.xml",
            description="Check workspace task.",
            default_file_grp="MAX"
        ))
        self.client.post("/api/tasks/1/run")
        result_response = self.client.get("/api/tasks/1/results")
        max_file_dir = os.path.join(result_response.json["result_dir"], "MAX")
        max_files = os.listdir(max_file_dir)
        with open(os.path.join(max_file_dir, max_files[2]), "rb") as img_file:
            content = img_file.read()
            assert content.startswith(b"\xff\xd8\xff\xe0\x00\x10JFIF")

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    @require_ocrd_processors(
        "ocrd-tesserocr-segment-region",
        "ocrd-tesserocr-segment-line",
        "ocrd-tesserocr-segment-word",
        "ocrd-tesserocr-recognize",
    )
    def test_task_tesserocr(self, mock_run_task):
        """Check if a new task is created."""
        response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.t_workflow(),
            src="http://foo.bar/mets.xml",
            description="Tesserocr task."
        ))

        response = self.client.post("/api/tasks/1/run")
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/1/status")
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/1/results")
        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-SEG-REGION")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<pc:Unicode>" in text

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    @require_ocrd_processors(
        "ocrd-tesserocr-segment-region",
        "ocrd-tesserocr-segment-line",
        "ocrd-tesserocr-segment-word",
        "ocrd-calamari-recognize",
    )
    def test_task_tess_cal(self, mock_run_task):
        """Check if a new task is created."""
        workflow_response = self.client.post("/api/workflows", json=dict(
            name="TC Workflow",
            description="Workflow with tesseract and calamari recog.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-calamari-recognize"
            ]
        ))

        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=workflow_response.json["id"],
            src="http://foo.bar/mets.xml",
            description="Tesserocr calamari task.",
            parameters={
                "ocrd-calamari-recognize": {
                    "checkpoint": "{0}/calamari_models/*ckpt.json".format(
                        CURRENT_DIR)
                }
            }
        ))

        response = self.client.post("/api/tasks/{0}/run".format(
            task_response.json["uid"]))
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/{0}/results".format(
            task_response.json["id"]))

        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<pc:Unicode>" in text

    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    @require_ocrd_processors(
        'ocrd-olena-binarize',
        'ocrd-tesserocr-segment-region',
        'ocrd-tesserocr-segment-line',
        'ocrd-calamari-recognize',
    )
    def test_task_ole_cal(self, mock_run_task):
        """Currently using /opt/calamari_models/fraktur_historical/0.ckpt.json
           as checkpoint file.
        """
        assert os.path.exists(
            "{0}/calamari_models/0.ckpt.json".format(CURRENT_DIR)
        )

        workflow_response = self.client.post("/api/workflows", json=dict(
            name="TC Workflow",
            description="Workflow with olena binarization, tesseract segmentation"
                        " and calamari recog.",
            processors=[
                "ocrd-olena-binarize",
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-calamari-recognize"
            ],
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                }
            }
        ))

        assert workflow_response.json == {'id': 1, 'message': 'Workflow created.'}

        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=workflow_response.json["id"],
            src="http://foo.bar/mets.xml",
            description="Olena calamari task.",
            parameters={
                "ocrd-olena-binarize": {
                    "impl": "sauvola-ms-split"
                },
                "ocrd-calamari-recognize": {
                    "checkpoint": "{0}/calamari_models/*.ckpt.json".format(
                        CURRENT_DIR)
                }
            }
        ))

        assert task_response.status_code == 201
        assert task_response.json["id"] == 1
        assert len(task_response.json["uid"]) == 36
        assert task_response.json["message"] == "Task created."

        response = self.client.post(
            "/api/tasks/{0}/run".format(task_response.json["id"])
        )
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get("/api/tasks/{0}/results".format(
            task_response.json["uid"]))

        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(
            os.path.join(ocr_results, result_files[2]), encoding='utf-8'
        ) as result_file:
            text = result_file.read()
            assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<pc:Unicode>" in text
