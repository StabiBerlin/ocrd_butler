import os
from datetime import datetime
from datetime import timedelta
import json
import glob
import zipfile
import io
import pathlib
import requests

from json2html import json2html

from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, Response, send_file, current_app

import xml.etree.ElementTree as ET

from ocrd_butler import celery

from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.api.processors import PROCESSORS_VIEW

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task

frontend = Blueprint("frontend", __name__)

@frontend.context_processor
def utility_processor():
    return dict(json2html=json2html,
                type=type,
                list=list,
                dict=dict)

@frontend.route("/")
def index():
    """Define our index page."""
    return render_template("index.html")

@frontend.app_errorhandler(404)
def not_found(err):
    """Define our custom 404 page."""
    return render_template("404.html", error=err)

@frontend.app_errorhandler(500)
def handle_500(err):
    """Define our custom 500 page."""
    import traceback
    return render_template(
        "500.html",
        error=err,
        exception=err.original_exception,
        traceback=traceback.format_exc()), 500

@frontend.route("/processors")
def processors():
    """Define the page presenting the integrated processors."""
    return render_template(
        "processors.html",
        processors=PROCESSORS_VIEW)

@frontend.route("/chains")
def chains():
    """Define the page presenting the configured chains."""
    results = db_model_Chain.query.all()

    current_chains = [{
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "processors": json.loads(c.processors)
        } for c in results]

    return render_template(
        "chains.html",
        chains=current_chains)

@frontend.route('/chain/delete/<int:chain_id>')
def delete_chain(chain_id):
    # TODO: Move functionality to api.
    db_model_Chain.query.filter_by(id=chain_id).delete()
    db.session.commit()

    return redirect("/chains", code=302)

def current_tasks():
    results = db_model_Task.query.all()

    current_tasks = []

    for result in results:

        chain = db_model_Chain.query.filter_by(id=result.chain_id).first()

        task = {
            "id": result.id,
            "work_id": result.work_id,
            "mets_url": result.mets_url,
            "file_grp": result.file_grp,
            "worker_id": result.worker_id,
            "chain": chain,
            "parameter": result.parameter,
            "result": {
                "status": "",
                "ready": False,
                "xml": "",
                "text": "",
                "received": "",
                "started": "",
                "succeeded": "",
                "runtime": ""
            }
        }

        res = celery.AsyncResult(result.worker_id)
        task["result"]["status"] = res.status,
        task["result"]["ready"] = res.status == "SUCCESS",

        if res.ready() and res.successful():
            task["result"].update({
                "xml": "/download/xml/{}".format(result.worker_id),
                "txt": "/download/txt/{}".format(result.worker_id),
            })

        backend_res = requests.get("http://localhost:5555/api/task/info/{0}".format(
            result.worker_id
        ))
        if backend_res.status_code == 200:
            info = json.loads(backend_res.content)
            task["result"].update({
                "received": datetime.fromtimestamp(info["received"])
            })
            if not info["state"] == "PENDING":
                task["result"].update({
                    "started": datetime.fromtimestamp(info["started"])
                })
            if info["state"] == "SUCCESS":
                task["result"].update({
                    "succeeded": datetime.fromtimestamp(info["succeeded"]),
                    "runtime": timedelta(seconds=info["runtime"])
                })

        current_tasks.append(task)

    return current_tasks


@frontend.route('/tasks')
def tasks():
    """Define the page presenting the created tasks."""

    return render_template(
        "tasks.html",
        tasks=current_tasks())


@frontend.route('/task/delete/<int:task_id>')
def task_delete(task_id):
    # TODO: Move functionality to api.
    db_model_Task.query.filter_by(id=task_id).delete()
    db.session.commit()

    return redirect("/tasks", code=302)


@frontend.route("/download/txt/<string:worker_id>")
def download_txt(worker_id):
    """Define route to download the results as text."""
    # TODO: we have to have the result (destination) dir in the result of the worker
    result = celery.AsyncResult(worker_id)
    dst_dir = "{}".format(result.result["result_dir"])

    # Get the output group of the last step in the chain of the task.
    task = db_model_Task.query.filter_by(worker_id=result.id).first()
    chain = db_model_Chain.query.filter_by(id=task.chain_id).first()
    last_step = json.loads(chain.processors)[-1]
    last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

    page_xml_dir = os.path.join(dst_dir, last_output)
    fulltext = ""

    namespace = {
        "page_2009-03-16": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2009-03-16",
        "page_2010-01-12": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-01-12",
        "page_2010-03-19": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2010-03-19",
        "page_2013-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
        "page_2016-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2016-07-15",
        "page_2017-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2017-07-15",
        "page_2018-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2018-07-15",
        "page_2019-07-15": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"
    }
    for file in glob.glob("{}/*.xml".format(page_xml_dir)):
        tree = ET.parse(file)
        xmlns = tree.getroot().tag.split("}")[0].strip("{")
        if xmlns in namespace.values():
            for regions in tree.iterfind(".//{%s}TextEquiv" % xmlns):
                fulltext += "\n"
                for region in regions.findall("{%s}Unicode" % xmlns):
                    if region.text is not None:
                        fulltext += region.text

    return Response(
        fulltext,
        mimetype="text/txt",
        headers={
            "Content-Disposition":
            "attachment;filename=fulltext_%s.txt" % result.result["task_id"]
        }
    )


@frontend.route("/download/xml/<string:worker_id>")
def download_xml_zip(worker_id):
    """Define route to download the page xml results as zip file."""
    # TODO: we have to have the result (destination) dir in the result of the worker
    result = celery.AsyncResult(worker_id)
    dst_dir = "{}".format(result.result["result_dir"])

    # Get the output group of the last step in the chain of the task.
    task = db_model_Task.query.filter_by(worker_id=result.id).first()
    chain = db_model_Chain.query.filter_by(id=task.chain_id).first()
    last_step = json.loads(chain.processors)[-1]
    last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

    page_xml_dir = os.path.join(dst_dir, last_output)
    base_path = pathlib.Path(page_xml_dir)

    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as z:
        for f_name in base_path.iterdir():
            z.write(f_name)
    data.seek(0)

    return send_file(
        data,
        mimetype="application/zip",
        as_attachment=True,
        attachment_filename="ocr_page_xml_%s.zip" % result.result["task_id"]
    )

@frontend.app_template_filter('format_date')
def _jinja2_filter_format_date(date, fmt="%d.%m.%Y, %H:%M"):
    return date.strftime(fmt)

@frontend.app_template_filter('format_delta')
def _jinja2_filter_format_delta(delta):
    return delta.__str__()
