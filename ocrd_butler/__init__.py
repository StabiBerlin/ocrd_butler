# -*- coding: utf-8 -*-

"""Top-level package for ocrd_butler."""

__author__ = """Marco Scheidhuber"""
__email__ = 'marco.scheidhuber@sbb.spk-berlin.de'
__version__ = '0.1.0'


from celery import Celery
from ocrd_butler.util import get_config_json

config_json = get_config_json()


def make_celery(app_name=__name__):
    """
    Creates a celery application.

    Args:
        app_name (String): application name
    Returns:
        celery object
    """
    return Celery(app_name,
                  backend=config_json['CELERY_RESULT_BACKEND_URL'],
                  broker=config_json['CELERY_BROKER_URL'])

# The base celery object of the app.
celery = make_celery()
