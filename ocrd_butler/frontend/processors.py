from flask import Blueprint
from flask import render_template

from json2html import json2html

from ocrd_butler.api.processors import PROCESSORS_VIEW
from ocrd_butler.frontend import frontend

processors_blueprint = Blueprint("processors_blueprint", __name__)

@processors_blueprint.context_processor
def utility_processor():
    return dict(json2html=json2html,
                type=type,
                list=list,
                dict=dict)


@processors_blueprint.route("/processors")
def processors():
    """Define the page presenting the integrated processors."""
    return render_template(
        "processors.html",
        processors=PROCESSORS_VIEW)
