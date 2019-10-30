import json
from flask import Blueprint, render_template, flash, redirect, url_for, jsonify

from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.processors import PROCESSORS

from ocrd_butler.database.models import Chain as db_model_Chain

frontend = Blueprint('frontend', __name__)

@frontend.route('/')
def index():
    return render_template('index.html')

@frontend.route('/processors')
def processors():
    return render_template(
        'processors.html',
        processors=PROCESSORS)

@frontend.route('/chains')
def chains():
    results = db_model_Chain.query.all()

    current_chains = [{
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "processors": json.loads(c.processors)
        } for c in results]

    return render_template(
        'chains.html',
        chains=current_chains)
