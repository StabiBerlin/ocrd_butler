# -*- coding: utf-8 -*-

"""Main module."""

import json
import os
import sys
import subprocess
import time

import logging.config

from flask import Flask, request, jsonify, Blueprint

from flask_sqlalchemy import SQLAlchemy

import ocrd_butler
from ocrd_butler import factory
from ocrd_butler.util import get_config_json
from ocrd_butler.api.restplus import api

from ocrd_butler.database import db

flask_app = factory.create_app(celery=ocrd_butler.celery)

config_json = get_config_json()
flask_app.config.update(config_json)
if not os.path.exists(flask_app.config["OCRD_BUTLER_RESULTS"]):
    os.makedirs(flask_app.config["OCRD_BUTLER_RESULTS"])

logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)

# our database
flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'

def initialize_app(flask_app):
    from ocrd_butler.api.tasks import ns as task_namespace
    # configure_app(flask_app)

    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(blueprint)
    api.add_namespace(task_namespace)
    flask_app.register_blueprint(blueprint)

    db.init_app(flask_app)
    db.create_all(app=flask_app)

def main():
    initialize_app(flask_app)
    log.info('>>>>> Starting development server at http://{}/api/ <<<<<'.format(
        flask_app.config['SERVER_NAME']))
    # flask_app.run(debug=settings.FLASK_DEBUG)
    # flask_app.run(debug=config_json["FLASK_DEBUG"])
    flask_app.run(debug=False)

if __name__ == "__main__":
    main()
