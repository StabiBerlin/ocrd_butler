# -*- coding: utf-8 -*-

"""Helper script to get celery running."""

from ocrd_butler import celery
from ocrd_butler.app import flask_app
from ocrd_butler.celery_utils import init_celery
# next one is important to get tasks initialized
from ocrd_butler.execution.tasks import run_task  # noqa

init_celery(celery, flask_app)
