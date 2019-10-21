# -*- coding: utf-8 -*-

"""Flask app factory with possible celery integration."""

from flask import Flask
import os

from ocrd_butler.celery_utils import init_celery

PKG_NAME = os.path.dirname(os.path.realpath(__file__)).split("/")[-1]


def create_app(app_name=PKG_NAME, **kwargs):
    """
    Creates a flask application.

    Args:
        app_name (String): application name, defaults to package name
    Returns:
        flask object
    """
    ocrd_butler = Flask(app_name)
    if kwargs.get("celery"):
        init_celery(kwargs.get("celery"), ocrd_butler)
    return ocrd_butler
