# -*- coding: utf-8 -*-

"""Console script for ocrd_butler."""
import os
import sys
import click
from ocrd_butler.app import flask_app, initialize_app, log
from flask import Flask
from flask.cli import FlaskGroup

@click.group(cls=FlaskGroup, create_app=flask_app)
def main(args=None):
    initialize_app(flask_app)
    log.info('>>>>> Starting development server at http://{}/api/ <<<<<'.format(
        flask_app.config['SERVER_NAME']))
    # flask_app.run(debug=settings.FLASK_DEBUG)
    # flask_app.run(debug=config_json["FLASK_DEBUG"])
    flask_app.run(debug=False)
    return 0



COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

@click.command('foobar')
@click.option('--coverage/--no-coverage', default=False,
              help='Run tests under code coverage.')
@click.argument('test_names', nargs=-1)
def test(coverage, test_names):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import subprocess
        os.environ['FLASK_COVERAGE'] = '1'
        sys.exit(subprocess.call(sys.argv))

    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
