# -*- coding: utf-8 -*-

"""Flask app factory with possible celery integration."""

from flask import Flask
import os

from ocrd_butler.celery_utils import init_celery

PKG_NAME = os.path.dirname(os.path.realpath(__file__)).split("/")[-1]


def create_app(app_name=PKG_NAME, config=None, **kwargs):
    """
    Creates a flask application.

    Args:
        app_name (String): application name, defaults to package name
    Returns:
        flask object
    """
    app = Flask(app_name)

    # Update the app configuration.
    if config is not None:
        app.config.from_object(config)

    # Supress flask_sqlalchemy warning.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if kwargs.get("celery"):
        init_celery(kwargs.get("celery"), app)

    return app
