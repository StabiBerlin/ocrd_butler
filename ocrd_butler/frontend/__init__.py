import os
import json
import glob
import zipfile
import io
import pathlib

from json2html import json2html

from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, Response, send_file

import xml.etree.ElementTree as ET

from ocrd_butler import celery

from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.processors import PROCESSORS_VIEW

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

@frontend.route('/tasks')
def tasks():
    """Define the page presenting the created tasks."""
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
            "parameter": result.parameter,
            "result": None
        }

        res = celery.AsyncResult(result.worker_id)
        if res.ready() and res.successful():
            task["result"] = {
                "status": res.status,
                "xml": "/download/xml/{}".format(result.worker_id),
                "txt": "/download/txt/{}".format(result.worker_id),
            }

        current_tasks.append(task)

    return render_template(
        "tasks.html",
        tasks=current_tasks)


@frontend.route("/download/txt/<string:worker_id>")
def download_txt(worker_id):
    """Define route to download the results as text."""
    # TODO: we have to have the result (destination) dir in the result of the worker
    res = celery.AsyncResult(worker_id)
    dst_dir = "{}".format(res.result["result_dir"])
    page_xml_dir = os.path.join(dst_dir, "OCRD-RECOGNIZE")
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
            "attachment;filename=fulltext_%s.txt" % res.result["task_id"]
        }
    )


@frontend.route("/download/xml/<string:worker_id>")
def download_xml_zip(worker_id):
    """Define route to download the page xml results as zip file."""
    # TODO: we have to have the result (destination) dir in the result of the worker
    res = celery.AsyncResult(worker_id)
    dst_dir = "{}".format(res.result["result_dir"])
    page_xml_dir = os.path.join(dst_dir, "OCRD-RECOGNIZE")
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
        attachment_filename="ocr_page_xml_%s.zip" % res.result["task_id"]
    )
