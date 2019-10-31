import json

from ocrd_butler import celery

from flask import Blueprint, render_template, flash, redirect, url_for, jsonify

from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.processors import PROCESSORS

from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task


frontend = Blueprint('frontend', __name__)

@frontend.route('/')
def index():
    return render_template('index.html')

@frontend.app_errorhandler(404)
def not_found(err):
    return render_template("404.html", error=err)

@frontend.app_errorhandler(500)
def handle_500(err):
    import traceback
    return render_template(
        '500.html',
        error=err,
        exception=err.original_exception,
        traceback=traceback.format_exc()), 500

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

@frontend.route('/tasks')
def tasks():
    results = db_model_Task.query.all()

    current_tasks = []
    for result in results:
        task = {
            "id": result.id,
            "work_id": result.work_id,
            "mets_url": result.mets_url,
            "file_grp": result.file_grp,
            "worker_id": result.worker_id,
            "chain": result.chain.name,
            "result": None
        }
        foo
        res = celery.AsyncResult(result.worker_id)
        if res.ready() and res.successful():
            task["result"] = {
                "status": res.status,
                "xml": "/download/xml/{}".format(result.worker_id),
                "txt": "/download/txt/{}".format(result.worker_id),
            }

        current_tasks.append(task)


    return render_template(
        'tasks.html',
        tasks=current_tasks)
