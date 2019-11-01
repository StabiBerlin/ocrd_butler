# -*- coding: utf-8 -*-

"""Flask app factory with possible celery integration."""

import os

from flask import Flask
from flask import Blueprint

from flask_bootstrap import Bootstrap

from ocrd_butler.api.restplus import api
from ocrd_butler.celery_utils import init_celery
from ocrd_butler.database import db
from ocrd_butler.frontend import frontend
from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.tasks import ns as task_namespace
from ocrd_butler.config import DevelopmentConfig

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
    if config is None:
        app.config.from_object(DevelopmentConfig)
    else:
        app.config.from_object(config)

    # Supress flask_sqlalchemy warning.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if kwargs.get("celery"):
        init_celery(kwargs.get("celery"), app)

    initialize_app(app)

    return app

def initialize_app(app):
    """Prepare our app with the needed blueprints and database."""
    # configure_app(app)

    # log.info("> Starting development server at http://%s/api/ <<<<<" %
    #          app.config["SERVER_NAME"])

    blueprint_api = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(blueprint_api)
    app.register_blueprint(blueprint_api)

    api.add_namespace(task_namespace)

    # Initialize frontend.
    Bootstrap(app)
    nav.init_app(app)
    app.register_blueprint(frontend)

    db.init_app(app)
    db.create_all(app=app)

    if not os.path.exists(app.config["OCRD_BUTLER_RESULTS"]):
        os.makedirs(app.config["OCRD_BUTLER_RESULTS"])
