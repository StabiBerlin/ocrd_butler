# -*- coding: utf-8 -*-

"""Helper script to get celery running."""

from ocrd_butler import celery
from ocrd_butler.factory import create_app
from ocrd_butler.celery_utils import init_celery
# next one is important to get tasks initialized
from ocrd_butler.queue import tasks

app = create_app()
init_celery(celery, app)
