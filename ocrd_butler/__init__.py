# -*- coding: utf-8 -*-

"""Top-level package for ocrd_butler."""

__author__ = """Marco Scheidhuber"""
__email__ = 'marco.scheidhuber@sbb.spk-berlin.de'
__version__ = '0.1.0'


from celery import Celery
from ocrd_butler.config import ProductionConfig


def make_celery(app_name=__name__, config=None):
    """
    Creates a celery application.

    Args:
        app_name (String): application name
    Returns:
        celery object
    """
    if config is None:
        config = ProductionConfig()

    return Celery(app_name,
                  backend=config.CELERY_RESULT_BACKEND_URL,
                  broker=config.CELERY_BROKER_URL)

# The base celery object of the app.
celery = make_celery()
