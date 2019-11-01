# -*- coding: utf-8 -*-

"""Top-level package for ocrd_butler."""

__author__ = """Marco Scheidhuber"""
__email__ = 'marco.scheidhuber@sbb.spk-berlin.de'
__version__ = '0.1.0'

from celery import Celery
from ocrd_butler.config import DevelopmentConfig
from ocrd_butler.config import ProductionConfig
from ocrd_butler.config import TestingConfig

def make_celery(app_name=__name__, config=None):
    """
    Creates a celery application.

    Args:
        app_name (String): application name
    Returns:
        celery object
    """
    # TODO: Choose from an environment variable what config to use?
    if config is None:
        config = DevelopmentConfig()

    return Celery(app_name,
                  backend=config.CELERY_RESULT_BACKEND_URL,
                  broker=config.CELERY_BROKER_URL)

# The base celery object of the app.
celery = make_celery()
