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
    TextField,
    SubmitField,
    SelectField,
    SelectMultipleField,
    TextAreaField
)
from wtforms.validators import (
    DataRequired,
    Length
)

from ocrd_butler.api.processors import PROCESSOR_NAMES
from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.util import host_url


chains_blueprint = Blueprint("chains_blueprint", __name__)


class NewChainForm(FlaskForm):
    """Contact form."""
    name = StringField('Name', [
        DataRequired(),
        Length(min=4, message=("Your name has to be at least 4 letters."))])
    description = StringField('Description', [DataRequired()])
    processors = SelectMultipleField('Processors for chain')
    submit = SubmitField('Create new chain')


@chains_blueprint.route("/new-chain", methods=['POST'])
def new_chain():
    """TODO: The order of the processors is not preserved in the multiselect!
    """
    data = json.dumps({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "processors": request.form.getlist("processors"),
        "parameters": request.form.get("parameters")
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/chains".format(host_url(request)), data=data, headers=headers)
    if response.status_code in (200, 201):
        flash("New chain created.")
    else:
        flash("Can't create new chain. Status {0}, Error {1}".format(
            response.status_code, response.json()["message"]))
    return redirect("/chains", code=302)


@chains_blueprint.route("/chains")
def chains():
    """Define the page presenting the configured chains."""
    results = db_model_Chain.query.all()
    new_chain_form = NewChainForm(csrf_enabled=False)
    p_choices = [(name, name) for name in PROCESSOR_NAMES]
    new_chain_form.processors.choices = p_choices

    current_chains = []

    for c in results:
        parameters = json.dumps(c.parameters, indent=4, separators=(',', ': '))
        parameters = parameters.replace(' ', '&nbsp;')
        parameters = parameters.replace('\n', '<br />')
        current_chains.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "processors": c.processors,
            "parameters": parameters
        })

    return render_template(
        "chains.html",
        chains=current_chains,
        form=new_chain_form)

@chains_blueprint.route('/chain/delete/<int:chain_id>')
def delete_chain(chain_id):
    # TODO: Move functionality to api.
    db_model_Chain.query.filter_by(id=chain_id).delete()
    db.session.commit()

    return redirect("/chains", code=302)
