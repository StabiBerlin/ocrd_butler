# -*- coding: utf-8 -*-

"""Testing the api for `ocrd_butler` package."""

import pytest
import os
import responses

from flask_restx import fields
from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app, db
from ocrd_butler.api.models import task_model

class ApiTests(TestCase):
    """Test our api actions."""

    def setUp(self):
        db.create_all()


        testfiles = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "files")
        with open("{0}/sbb-mets-PPN821929127.xml".format(testfiles), "r") as tfh:
            responses.add(responses.GET, "http://foo.bar/mets.xml",
                          body=tfh.read(), status=200)
            tfh.close()
        with open("{0}/00000001.jpg".format(testfiles), "rb") as tfh:
            responses.add(responses.GET, "http://content.staatsbibliothek-berlin.de/dms/PPN821929127/800/0/00000001.jpg",
                          body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()
        with open("{0}/00000002.jpg".format(testfiles), "rb") as tfh:
            responses.add(responses.GET, "http://content.staatsbibliothek-berlin.de/dms/PPN821929127/800/0/00000002.jpg",
                          body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()
        with open("{0}/00000003.jpg".format(testfiles), "rb") as tfh:
            responses.add(responses.GET, "http://content.staatsbibliothek-berlin.de/dms/PPN821929127/800/0/00000003.jpg",
                          body=tfh.read(), status=200, content_type="image/jpg")
            tfh.close()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        # self.clearTestDir()

    def clearTestDir(self):
        config = TestingConfig()
        test_dirs = glob.glob("%s/*" % config.OCRD_BUTLER_RESULTS)
        for test_dir in test_dirs:
            shutil.rmtree(test_dir, ignore_errors=True)

    def create_app(self):
        return create_app(config=TestingConfig)

    def t_chain(self):
        response = self.client.post("/api/chains", json=dict(
            name="T Chain",
            description="Some foobar chain.",
            processors=[
                "ocrd-tesserocr-segment-region",
                "ocrd-tesserocr-segment-line",
                "ocrd-tesserocr-segment-word",
                "ocrd-tesserocr-recognize",
            ]
        ))
        return response.json["id"]

    @responses.activate
    def test_task_tesserocr(self):
        """Check if a new task is created."""
        response = self.client.post("/api/tasks", json=dict(
            chain_id=self.t_chain(),
            src="http://foo.bar/mets.xml",
            description="Tesserocr task."
        ))
        response = self.client.post("/api/tasks/1/run")
        assert response.status_code == 200

        assert response["json"]["task_id"] == "PPN80041750X"
        assert response["json"]["status"] == "STARTED"
        assert response["json"]["result_dir"].startswith(
            "/tmp/ocrd_butler_results_testing")

        import time
        count = 5
        while True:
            response = self.client.get("/api/tasks/1/status")
            if status == "SUCCESS":
                break
            else:
                time.sleep(5)
                count += 1

        response = self.client.get("/api/tasks/1/results")
        ocr_results = os.path.join(task["result_dir"], "OCR-D-OCR-TESS")
        result_files = os.listdir(ocr_results)
        with open(os.path.join(ocr_results, result_files[1])) as result_file:
            text = result_file.read()
            assert '<Label value="word" type="textequiv_level"/>' in text
            assert "<Unicode>Wittenberg:</Unicode>" in text
