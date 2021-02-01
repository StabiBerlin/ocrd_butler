"""
Routes for the chains.
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
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.util import host_url


chains_blueprint = Blueprint("chains_blueprint", __name__)


class NewChainForm(FlaskForm):
    """
    Describes the form to create a new chain via frontend.
    """
    name = StringField('Name', [
        DataRequired(),
        Length(min=4, message=("Your name has to be at least 4 letters."))])
    description = StringField('Description', [DataRequired()])
    processors = SelectMultipleField('Processors for chain')
    submit = SubmitField('Create new chain')


@chains_blueprint.route("/new-chain", methods=['POST'])
def new_chain():
    """
    Create a new chain from the data given in the form.

    TODO: The order of the processors is not preserved in the multiselect!
    """
    data = json.dumps({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "processors": request.form.getlist("processors"),
        "parameters": request.form.get("parameters")
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/chains".format(
        host_url(request)), data=data, headers=headers)
    if response.status_code in (200, 201):
        flash("New chain created.")
    else:
        flash("Can't create new chain. Status {0}, Error {1}".format(
            response.status_code, response.json()["message"]))
    return redirect("/chains", code=302)


@chains_blueprint.route("/chain/delete/<int:chain_id>")
def delete_chain(chain_id):
    """
    Delete the given chain.
    """
    url = "{0}api/chains/{1}".format(host_url(request), chain_id)
    response = requests.delete(url)

    if response.status_code == 200:
        flash(response.json()["message"])
    else:
        flash("Can't delete chain {0}. Status {1}, Error {2}".format(
            chain_id, response.status_code, response.json()["message"]))
    return redirect("/chains", code=302)


@chains_blueprint.route("/chains")
def chains():
    """
    The page presenting the existing chains.
    """
    results = db_model_Chain.query.all()
    new_chain_form = NewChainForm(csrf_enabled=False)
    p_choices = [(name, name) for name in PROCESSOR_NAMES]
    new_chain_form.processors.choices = p_choices

    current_chains = []

    for chain in results:
        parameters = json.dumps(chain.parameters, indent=4, separators=(',', ': '))
        parameters = parameters.replace(' ', '&nbsp;')
        parameters = parameters.replace('\n', '<br />')
        current_chains.append({
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "processors": chain.processors,
            "parameters": parameters
        })

    return render_template(
        "chains.html",
        chains=current_chains,
        form=new_chain_form)
