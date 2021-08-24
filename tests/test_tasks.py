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
