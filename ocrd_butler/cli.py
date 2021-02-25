# -*- coding: utf-8 -*-

"""Console script for ocrd_butler."""
import sys
import click
from ocrd_butler.app import flask_app
from ocrd_butler.util import logger

log = logger(__name__)


@click.command('start')
@click.option('--debug', default=False,
              help='Run app with debug enabled.')
def main(debug=False, args=None):
    """Start the app. We will see if we need this anyway."""
    log.info('>>>>> Starting development server at http://{}/api/ <<<<<'.format(
        flask_app.config['SERVER_NAME']))
    # flask_app.run(debug=settings.FLASK_DEBUG)
    # flask_app.run(debug=config_json["FLASK_DEBUG"])
    flask_app.run(debug=debug)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
