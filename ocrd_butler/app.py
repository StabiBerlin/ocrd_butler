# -*- coding: utf-8 -*-

"""Main module."""

import os
import logging.config

from flask import Blueprint
from flask_bootstrap import Bootstrap

import ocrd_butler
from ocrd_butler import make_celery
from ocrd_butler import factory
from ocrd_butler.api.restplus import api
from ocrd_butler.database import db

from ocrd_butler.frontend import frontend
from ocrd_butler.frontend.nav import nav

from ocrd_butler.config import DevelopmentConfig

config = DevelopmentConfig()
flask_app = factory.create_app(
    celery=make_celery(config=config),
    config=config)

if not os.path.exists(flask_app.config["OCRD_BUTLER_RESULTS"]):
    os.makedirs(flask_app.config["OCRD_BUTLER_RESULTS"])


logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)


def initialize_app(app):
    """Prepare our app with the needed blueprints and database."""
    from ocrd_butler.api.tasks import ns as task_namespace
    # configure_app(app)

    log.info("> Starting development server at http://%s/api/ <<<<<" %
             app.config["SERVER_NAME"])

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

initialize_app(flask_app)

def main():
    """What should I do, when I'm called directly?"""
    # initialize_app(flask_app)
    log.info("> Starting development server at http://%s/api/ <<<<<" %
             flask_app.config['SERVER_NAME'])
    # flask_app.run(debug=settings.FLASK_DEBUG)
    # flask_app.run(debug=config_json["FLASK_DEBUG"])
    flask_app.run(debug=False)

if __name__ == "__main__":
    main()
