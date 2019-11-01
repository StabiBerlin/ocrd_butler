# -*- coding: utf-8 -*-

"""Main module."""

import os
import logging.config

from flask import Blueprint
from flask_bootstrap import Bootstrap

from ocrd_butler import factory, make_celery
from ocrd_butler.api.restplus import api
from ocrd_butler.config import DevelopmentConfig
from ocrd_butler.database import db

from ocrd_butler.frontend import frontend
from ocrd_butler.frontend.nav import nav

config = DevelopmentConfig()
flask_app = factory.create_app(
    celery=make_celery(config=config),
    config=config)


logging_conf_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)




# factory.initialize_app(flask_app)

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
