"""
Routes for the workflows.
"""

import json
import requests

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request
)
from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    SubmitField,
    SelectMultipleField
)
from wtforms.validators import (
    DataRequired,
    Length
)

from ocrd_butler.api.processors import PROCESSOR_NAMES
from ocrd_butler.util import host_url


workflows_blueprint = Blueprint("workflows_blueprint", __name__)


class NewWorkflowForm(FlaskForm):
    """
    Describes the form to create a new workflow via frontend.
    """
    name = StringField('Name', [
        DataRequired(),
        Length(min=4, message=("Your name has to be at least 4 letters."))])
    description = StringField('Description', [DataRequired()])
    processors = SelectMultipleField('Processors for workflow')
    submit = SubmitField('Create new workflow')


@workflows_blueprint.route("/new-workflow", methods=['POST'])
def new_workflow():
    """
    Create a new workflow from the data given in the form.

    TODO: The order of the processors is not preserved in the multiselect!
    """
    data = json.dumps({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "processors": request.form.getlist("processors"),
        "parameters": request.form.get("parameters")
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/workflows".format(
        host_url(request)), data=data, headers=headers)
    if response.status_code in (200, 201):
        flash("New workflow created.")
    else:
        flash("Can't create new workflow. Status {0}, Error {1}".format(
            response.status_code, response.json()["message"]))
    return redirect("/workflows", code=302)


@workflows_blueprint.route("/workflow/delete/<int:workflow_id>")
def delete_workflow(workflow_id):
    """
    Delete the given workflow.
    """
    url = "{0}api/workflows/{1}".format(host_url(request), workflow_id)
    response = requests.delete(url)

    if response.status_code == 200:
        flash(response.json()["message"])
    else:
        flash("Can't delete workflow {0}. Status {1}, Error {2}".format(
            workflow_id, response.status_code, response.json()["message"]))
    return redirect("/workflows", code=302)


@workflows_blueprint.route("/workflows")
def workflows():
    """
    The page presenting the existing workflows.
    """
    results = requests.get(
        f"{host_url(request)}api/workflows"
    ).json
    new_workflow_form = NewWorkflowForm(meta={'csrf': False})
    p_choices = [(name, name) for name in PROCESSOR_NAMES]
    new_workflow_form.processors.choices = p_choices

    current_workflows = []

    for workflow in results:
        parameters = json.dumps(
            workflow.get('parameters', {}),
            indent=4, separators=(',', ': ')
        )
        parameters = parameters.replace(' ', '&nbsp;')
        parameters = parameters.replace('\n', '<br />')
        current_workflows.append({
            "id": workflow.get('id'),
            "name": workflow.get('name'),
            "description": workflow.get('description'),
            "processors": workflow.get('processors'),
            "parameters": parameters
        })

    return render_template(
        "workflows.html",
        workflows=current_workflows,
        form=new_workflow_form)
