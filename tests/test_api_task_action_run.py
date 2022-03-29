# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import os
import json
import glob
import responses
import shutil
from unittest import mock

from flask_testing import TestCase

from ocrd_butler import celery
from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import db
from ocrd_butler.app import flask_app

from . import require_ocrd_processors


CURRENT_DIR = os.path.dirname(__file__)


# https://medium.com/@scythargon/how-to-use-celery-pytest-fixtures-for-celery-intergration-testing-6d61c91775d9
# # @pytest.mark.usefixtures("config")
# @pytest.mark.usefixtures('celery_session_app')
# @pytest.mark.usefixtures('celery_session_worker')
class ApiTaskActionRunTests(TestCase):
    """Test our api actions."""

    def setUp(self):
        celery.conf.task_always_eager = True

        db.create_all()

        testfiles = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "files")

        with open(
                os.path.join(testfiles, "PPN821881744.mets.xml"),
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
                        "https://content.staatsbibliothek-berlin.de/dc/"
                        f"PPN821881744-0000000{i}/full/max/0/default.jpg"
                    ),
                    body=img_file,
                    status=200,
                    content_type="image/jpg"
                )
                responses.add(
                    method=responses.GET,
                    url=(
                        "https://content.staatsbibliothek-berlin.de/dc/"
                        f"PPN821881744-0000000{i}/full/max/0/default.tif"
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
        return flask_app

    def t_workflow(self):
        """Creates a workflow with tesseract processors."""
        response = self.client.post("/api/workflows", json=dict(
            name="T Workflow",
            description="Some foobar workflow.",
            processors=[
                {"name": "ocrd-tesserocr-segment-region"},
                {"name": "ocrd-tesserocr-segment-line"},
                {"name": "ocrd-tesserocr-segment-word"},
                {
                    "name": "ocrd-tesserocr-recognize",
                    "parameters": {
                        "model": "deu"
                    },
                    "output_file_grp": "OCR-D-SEG-WORD",
                },
            ],
        ))
        return response.json["id"]

    def r_workflow(self):
        """Creates a workflow with tesseract processors."""
        response = self.client.post("/api/workflows", json=dict(
            name="T Workflow",
            description="Some foobar workflow.",
            processors=[
                {
                    "name": "ocrd-tesserocr-recognize",
                    "parameters": {
                        "model": "deu"
                    },
                    "output_file_grp": "OCR-D-SEG-WORD",
                },
            ],
        ))
        return response.json["id"]

    def light_workflow(self):
        """Creates a workflow without processors."""
        response = self.client.post("/api/workflows", json=dict(
            name="Light Workflow",
            description="Empty but not useless workflow.",
            processors=[{
                "name": "ocrd-tesserocr-segment-region"
            }],
        ))
        return response.json["id"]

    @responses.activate
    def test_task_run_dummy(self):
        workflow_response = self.client.post(
            '/api/workflows',
            json=dict(
                name='dummy workflow',
                description='workflow containing only a dummy processor task',
                processors=[dict(
                    name='ocrd-dummy'
                )]
            )
        ).json
        assert workflow_response['message'] == 'Workflow created.'
        task_response = self.client.post(
            '/api/tasks',
            json=dict(
                workflow_id=workflow_response['id'],
                src="http://foo.bar/mets.xml",
            )
        ).json
        assert task_response['message'] == 'Task created.'
        self.add_response_action(task_response['uid'])
        run_response = self.client.post(
            f"/api/tasks/{task_response['uid']}/run"
        ).json
        assert run_response['status'] == 'SUCCESS'

    def add_response_action(self, uid, action='page_to_alto'):
        responses.add(
            method=responses.POST,
            url=(
                f"http://localhost/api/tasks/{uid}/{action}"
            ),
            body=json.dumps({
                "status": "SUCCESS",
                "msg": "works"
            }).encode('utf-8'),
            status=200,
            content_type="application/json"
        )

    @responses.activate
    @require_ocrd_processors(
        "ocrd-tesserocr-recognize",
    )
    def test_check_task_before_run(self):
        task_response = self.client.post(
            '/api/tasks',
            json=dict(
                workflow_id=self.r_workflow(),
                src="http://foo.bar/mets.xml",
            )
        ).json
        self.add_response_action(task_response['uid'])
        from ocrd_butler.execution.tasks import is_task_processing
        res = is_task_processing(task_response)
        assert res['processing'] == False
        run_response = self.client.post(
            f"/api/tasks/{task_response['uid']}/run"
        ).json
        # TODO: Exception: Processor ocrd-tesserocr-recognize failed with exit code 1.
        # res = is_task_processing(task_response)
        # assert res['processing'] == True

    @responses.activate
    @require_ocrd_processors("ocrd-tesserocr-segment-region")
    def test_task_max_file_download(self):
        """Check if max size images are downloaded."""
        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.light_workflow(),
            src="http://foo.bar/mets.xml",
            description="Check workspace task.",
            default_file_grp="MAX"
        ))
        self.add_response_action(task_response.json['uid'])

        self.client.post(f"/api/tasks/{task_response.json['uid']}/run")
        result_response = self.client.get(f"/api/tasks/{task_response.json['uid']}/results")
        max_file_dir = os.path.join(result_response.json["result_dir"], "MAX")
        max_files = os.listdir(max_file_dir)
        with open(os.path.join(max_file_dir, max_files[2]), "rb") as img_file:
            content = img_file.read()
            assert content.startswith(b"\xff\xd8\xff\xe0\x00\x10JFIF")

    @responses.activate
    @require_ocrd_processors("ocrd-tesserocr-segment-region")
    def test_task_status_change(self):
        """ Test task status life cycle.
        """
        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.light_workflow(),
            src="http://foo.bar/mets.xml",
            description="Check workspace task.",
            default_file_grp="DEFAULT"
        ))
        self.add_response_action(task_response.json['uid'])

        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/status")
        assert response.status_code == 200
        assert response.data == b'{\n  "status": "CREATED"\n}\n'

        response = self.client.post("/api/tasks/1/run")
        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/status")
        assert response.status_code == 200
        assert response.data == b'{\n  "status": "SUCCESS"\n}\n'

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
        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=self.t_workflow(),
            src="http://foo.bar/mets.xml",
            description="Tesserocr task."
        ))
        self.add_response_action(task_response.json['uid'])

        response = self.client.post(f"/api/tasks/{task_response.json['uid']}/run")
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/status")
        assert response.json["status"] == "SUCCESS"

        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/results")
        ocr_results = os.path.join(response.json["result_dir"],
                                   "03-OCRD-TESSEROCR-SEGMENT-WORD-OUTPUT")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[2])) as result_file:
            text = result_file.read()
            assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<pc:Word" in text

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
                {"name": "ocrd-tesserocr-segment-region"},
                {"name": "ocrd-tesserocr-segment-line"},
                {"name": "ocrd-tesserocr-segment-word"},
                {"name": "ocrd-calamari-recognize"},
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
        self.add_response_action(task_response.json['uid'])

        response = self.client.post(f"/api/tasks/{task_response.json['uid']}/run")
        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/results")

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
                {
                    "name": "ocrd-olena-binarize",
                    "parameters": {"impl": "sauvola-ms-split"}
                },
                {"name": "ocrd-tesserocr-segment-region"},
                {"name": "ocrd-tesserocr-segment-line"},
                {"name": "ocrd-calamari-recognize"},
            ]
        ))

        assert workflow_response.json["id"] == 1
        assert workflow_response.json["uid"] is not None
        assert workflow_response.json["message"] == "Workflow created."

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

        self.add_response_action(task_response.json['uid'])

        response = self.client.post(f"/api/tasks/{task_response.json['uid']}/run")

        assert response.status_code == 200
        assert response.json["status"] == "SUCCESS"

        response = self.client.get(f"/api/tasks/{task_response.json['uid']}/results")

        ocr_results = os.path.join(response.json["result_dir"],
                                   "OCR-D-OCR-CALAMARI")
        result_files = os.listdir(ocr_results)
        with open(
            os.path.join(ocr_results, result_files[2]), encoding='utf-8'
        ) as result_file:
            text = result_file.read()
            assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
            assert "<pc:Unicode>" in text


    @mock.patch("ocrd_butler.execution.tasks.run_task")
    @responses.activate
    @require_ocrd_processors(
        'ocrd-calamari-recognize'
    )
    def test_task_failed(self, mock_run_task):
        """Lets fail a processor and expect that the task fail as well.
        """

        workflow_response = self.client.post("/api/workflows", json=dict(
            name="Calamari Recognize",
            description="Calamari recognize only",
            processors=[
                { "name": "ocrd-calamari-recognize" }
            ]
        ))

        assert workflow_response.json["uid"] is not None
        assert workflow_response.json["message"] == "Workflow created."

        task_response = self.client.post("/api/tasks", json=dict(
            workflow_id=workflow_response.json["id"],
            src="http://foo.bar/mets.xml",
            description="Calamari recognize task to fail.",
            parameters={
                "ocrd-calamari-recognize": {
                    "checkpoint": "/foobar/*.ckpt.json"
                }
            }
        ))

        assert task_response.status_code == 201
        assert len(task_response.json["uid"]) == 36
        assert task_response.json["message"] == "Task created."

        self.add_response_action(task_response.json['uid'])

        response = self.client.post(f"/api/tasks/{task_response.json['uid']}/run")

        assert response.status_code == 200
        assert response.json["status"] == "FAILURE"
        assert "Processor ocrd-calamari-recognize failed with exit code 1." in response.json["traceback"]
