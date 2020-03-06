# -*- coding: utf-8 -*-

"""Main module."""

import os
import logging.config

from ocrd_butler import factory, make_celery
from ocrd_butler.config import DevelopmentConfig


config = DevelopmentConfig()
flask_app = factory.create_app(
    celery=make_celery(config=config),
    config=config)

logging_conf_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '../logging.conf'))
logging.config.fileConfig(logging_conf_path)
log = logging.getLogger(__name__)

#import faulthandler; faulthandler.enable()

def main():
    """What should I do, when I'm called directly?"""
    log.info("> Starting development server at http://%s/api/ <<<<<" %
             flask_app.config['SERVER_NAME'])
    flask_app.run(host="0.0.0.0", debug=False)

if __name__ == "__main__":
    main()
