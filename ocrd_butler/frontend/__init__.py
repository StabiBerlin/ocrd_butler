"""
Frontend definition with Flask and basic routes.
"""
import traceback

from flask import (
    Blueprint,
    render_template,
)
from flask_wtf import FlaskForm


frontend_blueprint = Blueprint("frontend_blueprint", __name__)


@frontend_blueprint.route("/")
def index():
    """Define our index page."""
    return render_template("index.html")

@frontend_blueprint.app_errorhandler(404)
def not_found(err):
    """Define our custom 404 page."""
    return render_template("404.html", error=err), 404

@frontend_blueprint.app_errorhandler(500)
def handle_500(err):
    """Define our custom 500 page."""
    return render_template(
        "500.html",
        error=err,
        exception=err.original_exception,
        traceback=traceback.format_exc()), 500
