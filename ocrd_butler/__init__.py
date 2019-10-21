# -*- coding: utf-8 -*-

"""Top-level package for ocrd_butler."""

__author__ = """Marco Scheidhuber"""
__email__ = 'marco.scheidhuber@sbb.spk-berlin.de'
__version__ = '0.1.0'


from celery import Celery

def make_celery(app_name=__name__):
    """
    Creates a celery application.

    Args:
        app_name (String): application name
    Returns:
        celery object
    """
    redis_uri = "redis://localhost:6379"
    return Celery(app_name,
                    backend=redis_uri,
                    broker=redis_uri)

celery = make_celery()
