# -*- coding: utf-8 -*-

"""Main module."""

from ocrd_butler import (
    factory,
    make_celery,
    config,
)
from ocrd_butler.util import logger


flask_app = factory.create_app(
    celery=make_celery(config=config),
    config=config)


def main():
    """What should I do, when I'm called directly?"""
    logger.info("> Starting development server at http://%s/api/ <<<<<" %
             flask_app.config['SERVER_NAME'])
    flask_app.run(host="0.0.0.0", debug=True)


if __name__ == "__main__":
    main()
