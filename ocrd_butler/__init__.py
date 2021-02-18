# -*- coding: utf-8 -*-

"""Top-level package for ocrd_butler."""

__author__ = """Marco Scheidhuber"""
__email__ = 'marco.scheidhuber@sbb.spk-berlin.de'
__version__ = '0.1.0'

from celery import Celery

from . import config as butler_config


def get_config() -> butler_config.Config:
    """ Returns one of ``DevelopmentConfig``, ``TestingConfig``, or ``ProductionConfig``,
    based on the ``PROFILE`` environment variable.
    ``PROFILE`` may take the values ``DEV``, ``TEST``, or ``PROD``.
    If variable is not set, ``DEV`` is being assumed.
    """
    return butler_config.profile_config()


def make_celery(app_name=__name__, config=None):
    """
    Creates a celery application.

    Args:
        app_name (String): application name
    Returns:
        celery object
    """
    config = config or get_config()

    return Celery(app_name,
                  backend=config.CELERY_RESULT_BACKEND_URL,
                  broker=config.CELERY_BROKER_URL)


config = get_config()
# The base celery object of the app.
celery = make_celery()
