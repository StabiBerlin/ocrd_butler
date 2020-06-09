import os
from datetime import datetime
from datetime import timedelta
import json
import glob
import zipfile
import io
import pathlib
import requests
import shelve
import subprocess
from shutil import copyfile
from json2html import json2html

from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, Response, send_file, current_app, request
from flask_wtf import FlaskForm
from wtforms import StringField, TextField, SubmitField, SelectField, SelectMultipleField, TextAreaField
from wtforms.widgets import Select
from wtforms.validators import DataRequired, Length, URL

import xml.etree.ElementTree as ET

from ocrd.processor.base import run_cli
from ocrd.resolver import Resolver

from ocrd_butler import celery

from ocrd_butler.frontend.nav import nav
from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.api.processors import PROCESSORS_VIEW
from ocrd_butler.api.processors import PROCESSOR_NAMES

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task

from ocrd_butler.util import host_url

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
    return render_template("404.html", error=err), 404

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

class NewChainForm(FlaskForm):
    """Contact form."""
    name = StringField('Name', [
        DataRequired(),
        Length(min=4, message=("Your name has to be at least 4 letters."))])
    description = StringField('Description', [DataRequired()])
    processors = SelectMultipleField('Processors for chain')
    submit = SubmitField('Create new chain')

@frontend.route("/new-chain", methods=['POST'])
def new_chain():
    data = json.dumps({
        "name": request.form.get("name"),
        "description": request.form.get("description"),
        "processors": request.form.getlist("processors")
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/chains".format(host_url(request)), data=data, headers=headers)
    if response.status_code in (200, 201):
        flash("New chain created.")
    else:
        flash("Can't create new chain. Status {0}, Error {1}".format(
            response.status_code, response.json()["message"]))
    return redirect("/chains", code=302)


@frontend.route("/chains")
def chains():
    """Define the page presenting the configured chains."""
    results = db_model_Chain.query.all()
    new_chain_form = NewChainForm(csrf_enabled=False)
    p_choices = [(name, name) for name in PROCESSOR_NAMES]
    new_chain_form.processors.choices = p_choices

    current_chains = [{
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "processors": c.processors
        } for c in results]

    return render_template(
        "chains.html",
        chains=current_chains,
        form=new_chain_form)

@frontend.route('/chain/delete/<int:chain_id>')
def delete_chain(chain_id):
    # TODO: Move functionality to api.
    db_model_Chain.query.filter_by(id=chain_id).delete()
    db.session.commit()

    return redirect("/chains", code=302)


def task_information(uid):
    """Get information for the task based on its uid."""
    response = requests.get("http://localhost:5555/api/task/info/{0}".format(uid))
    if response.status_code == 404:
        current_app.logger.warning("Can't find task '{0}'".format(uid))
        return None
    try:
        task_info = json.loads(response.content)
    except json.decoder.JSONDecodeError as exc:
        current_app.logger.error("Can't read response for task '{0}'. ({1})".format(
            uid, exc.__str__()))
        return None

    task_info["ready"] = task_info["state"] == "SUCCESS"
    if task_info["result"] is not None:
        task_info["result"] = json.loads(task_info["result"].replace("'", '"'))

    return task_info


def current_tasks():
    results = db_model_Task.query.all()

    tasks = []

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
                "page": "",
                "alto": "",
                "text": "",
                "received": "",
                "started": "",
                "succeeded": "",
                "runtime": ""
            }
        }

        task_info = task_information(result.worker_id)

        if task_info is not None and task_info["ready"]:
            task["result"].update({
                "page": "/download/page/{}".format(result.worker_id),
                "alto": "/download/alto/{}".format(result.worker_id),
                "txt": "/download/txt/{}".format(result.worker_id),
            })

            if task_info["received"] is not None:
                task["result"].update({
                    "received": datetime.fromtimestamp(task_info["received"])
                })

            if task_info["started"] is not None:
                task["result"].update({
                    "started": datetime.fromtimestamp(task_info["started"])
                })

            if task_info["succeeded"] is not None:
                task["result"].update({
                    "succeeded": datetime.fromtimestamp(task_info["succeeded"]),
                    "runtime": timedelta(seconds=task_info["runtime"])
                })

        task["flower_url"] = "{0}{1}task/{2}".format(
            request.host_url.replace("5000", "5555"), # A bit hacky, but for devs on localhost.
            "flower/" if not "localhost:5000" in request.host_url else "",
            task["worker_id"]
        )

        tasks.append(task)

    return tasks

class NewTaskForm(FlaskForm):
    """Contact form."""
    task_id = StringField("Task ID", [
        DataRequired(),
        Length(min=4, message=("The task has to be at least 4 letters."))])
    mets_url = StringField("METS URL",
                validators=[
                    DataRequired(message="Please enter an URL to a METS file."),
                    URL(message="Please enter a valid URL to a METS file.")
                ])
    input_file_grp = StringField("Input file group (defaults to 'DEFAULT')")
    chain = SelectField('Chain',
                validators=[
                    DataRequired(message="Please choose a chain.")
                ])
    parameter = TextAreaField('Parameter')
    submit = SubmitField('Create new task')

@frontend.route("/new-task", methods=['POST'])
def new_task():
    # TODO: Adjust task model works_id => id!
    parameter = request.form.get("parameter")

    if parameter:
        parameter = json.loads(parameter)

    data = json.dumps({
        "id": request.form.get("task_id"),
        "mets_url": request.form.get("mets_url"),
        "file_grp": request.form.get("input_file_grp") or "DEFAULT",
        "chain": request.form.get("chain"),
        "parameter": parameter
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/tasks".format(host_url(request)), data=data, headers=headers)
    if response.status_code in (200, 201):
        flash("New task created.")
    else:
        result = response.json()
        flash("Can't create new task. Status {0}, Error '{1}': '{2}'.".format(
            result["statusCode"], result["message"], result["status"]))
    return redirect("/tasks", code=302)


@frontend.route('/tasks', methods=['GET'])
def tasks():
    """Define the page presenting the created tasks."""
    # new_task_form = NewTaskForm(csrf_enabled=False)
    new_task_form = NewTaskForm()
    chains = db_model_Chain.query.all()
    new_task_form.chain.choices = [(chain.name, chain.name) for chain in chains]

    return render_template(
        "tasks.html",
        tasks=current_tasks(),
        form=new_task_form)


class CompareForm(FlaskForm):
    """Contact form."""
    task_from = SelectMultipleField("Task from",
        validators=[DataRequired(message="Please choose a task to compare from.")],
        widget=Select(multiple=False))
    task_to = SelectField("Task to",
        validators=[DataRequired(message="Please choose a task to compare to.")])
    submit = SubmitField('Compare tasks')

@frontend.route("/compare", methods=["GET"])
def compare():
    compare_form = CompareForm()
    tasks = db_model_Task.query.all()
    compare_form.task_from.choices = [(task.id, task.work_id) for task in tasks]
    compare_form.task_to.choices = [(task.id, task.work_id) for task in tasks]

    return render_template(
        "compare.html",
        form=compare_form)

@frontend.route('/compare', methods=['POST'])
def compare_results():
    """Define the page presenting the created tasks."""

    # 1. We copy the files to compare in an own folder and use dinglehopper
    #    to produce html files.
    #    ▶ dinglehopper [OPTIONS] GT OCR [REPORT_PREFIX]
    # 2. We add the files as (fake) GT data to the mets files and use ocrd-dinglehopper.
    #    to get the results in the mets file.
    #    ▶ ocrd-dinglehopper -m mets.xml -I OCR-D-GT-PAGE,OCR-D-OCR-TESS -O OCR-D-OCR-TESS-EVAL
    # 3. We create an own mets file for this, copy there (fake) GT and (other) OCR and
    #    use also ocrd-dinglehopper.
    task_from_id = request.form.get("task_from")
    task_to_id = request.form.get("task_to")
    if task_from_id == task_to_id:
        # not making sense to compare to itself, but why not?
        pass

    task_from = db_model_Task.query.filter_by(id=task_from_id).first()
    task_to = db_model_Task.query.filter_by(id=task_to_id).first()

    result_from = task_information(task_from.worker_id)
    result_to = task_information(task_to.worker_id)

    dst_dir = "{0}-{1}".format(
        result_from["result"]["result_dir"],
        os.path.basename(result_to["result"]["result_dir"]))

    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)

    # Get the output group of the last step in the chain of the task.
    chain_from = db_model_Chain.query.filter_by(id=task_from.chain_id).first()
    last_proc_from = json.loads(chain_from.processors)[-1]
    last_output_from = PROCESSORS_ACTION[last_proc_from]["output_file_grp"]
    chain_to = db_model_Chain.query.filter_by(id=task_to.chain_id).first()
    last_proc_to = json.loads(chain_to.processors)[-1]
    last_output_to = PROCESSORS_ACTION[last_proc_to]["output_file_grp"]

    # TODO: collect informations to this task
    results_from_path = "{0}/{1}/*".format(result_from["result"]["result_dir"], last_output_from)
    for file in glob.glob(results_from_path):
        copyfile(file, "{0}/FROM-{1}".format(dst_dir, os.path.basename(file)))
    results_to_path = "{0}/{1}/*".format(result_to["result"]["result_dir"], last_output_to)
    for file in glob.glob(results_to_path):
        copyfile(file, "{0}/TO-{1}".format(dst_dir, os.path.basename(file)))

    dinglehop_path = "{0}/FROM-*".format(dst_dir)
    for count, file in enumerate(glob.glob(dinglehop_path)):
        # dinglehopper [OPTIONS] GT OCR [REPORT_PREFIX]
        cmd = "dinglehopper {0} {1} RESULT-{2}".format(
            os.path.basename(file),
            os.path.basename(file.replace("FROM-", "TO-").replace(last_output_from, last_output_to)),
            "{}".format(count).zfill(4))
        try:
            subprocess.check_output([cmd], shell=True, cwd=dst_dir)
        except subprocess.CalledProcessError as exc:
            print ('ERROR: {}'.format(exc.__str__()))

    results = []
    for count, file in enumerate(glob.glob("{}/RESULT-*.html".format(dst_dir))):
        results.append(open(file, 'r').read())

    return render_template(
        "compare_results.html",
        results=results)

@frontend.route("/task/delete/<int:task_id>")
def task_delete(task_id):
    """Delete the task with the given id."""
    response = requests.delete("{0}api/tasks/task/{1}".format(
        host_url(request),
        task_id))
    if response.status_code in (200, 201):
        flash("Task {0} deleted.".format(task_id))
    else:
        result = json.loads(response.content)
        flash("An error occured: {0}".format(result.status))
    return redirect("/tasks", code=302)


@frontend.route("/download/txt/<string:worker_id>")
def download_txt(worker_id):
    """Define route to download the results as text."""
    task_info = task_information(worker_id)

    # Get the output group of the last step in the chain of the task.
    task = db_model_Task.query.filter_by(worker_id=worker_id).first()
    chain = db_model_Chain.query.filter_by(id=task.chain_id).first()
    last_step = json.loads(chain.processors)[-1]
    last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

    page_xml_dir = os.path.join(task_info["result"]["result_dir"], last_output)
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
            "attachment;filename=fulltext_%s.txt" % task_info["result"]["task_id"]
        }
    )


@frontend.route("/download/page/<string:worker_id>")
def download_page_zip(worker_id):
    """Define route to download the page xml results as zip file."""
    task_info = task_information(worker_id)

    # Get the output group of the last step in the chain of the task.
    task = db_model_Task.query.filter_by(worker_id=worker_id).first()
    chain = db_model_Chain.query.filter_by(id=task.chain_id).first()
    last_step = json.loads(chain.processors)[-1]
    last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

    page_xml_dir = os.path.join(task_info["result"]["result_dir"], last_output)
    base_path = pathlib.Path(page_xml_dir)

    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as zip_file:
        for f_name in base_path.iterdir():
            arcname = "{0}/{1}".format(last_output, os.path.basename(f_name))
            zip_file.write(f_name, arcname=arcname)
    data.seek(0)

    return send_file(
        data,
        mimetype="application/zip",
        as_attachment=True,
        attachment_filename="ocr_page_xml_%s.zip" % task_info["result"]["task_id"]
    )

@frontend.route("/download/alto/<string:worker_id>")
def download_alto_zip(worker_id):
    """Define route to download the alto xml results as zip file."""
    task_info = task_information(worker_id)

    # Get the output group of the last step in the chain of the task.
    task = db_model_Task.query.filter_by(worker_id=worker_id).first()
    chain = db_model_Chain.query.filter_by(id=task.chain_id).first()
    last_step = json.loads(chain.processors)[-1]
    last_output = PROCESSORS_ACTION[last_step]["output_file_grp"]

    # BUG?: java.lang.IllegalArgumentException:
    # Variable value 'TextTypeSimpleType.CAPTION' is not in the list of valid values.
    # possible reason: https://github.com/OCR-D/core/issues/451 ??
    alto_xml_dir = os.path.join(task_info["result"]["result_dir"], "OCR-D-OCR-ALTO")
    alto_path = pathlib.Path(alto_xml_dir)

    if not os.path.exists(alto_path):
        mets_url = "{}/mets.xml".format(task_info["result"]["result_dir"])
        run_cli(
            "ocrd-fileformat-transform",
            mets_url=mets_url,
            resolver=Resolver(),
            log_level="DEBUG",
            input_file_grp=last_output,
            output_file_grp="OCR-D-OCR-ALTO",
            parameter='{"from-to": "page alto"}'
        )

    data = io.BytesIO()
    with zipfile.ZipFile(data, mode='w') as zip_file:
        for f_name in alto_path.iterdir():
            arcname = "{0}/{1}".format(last_output, os.path.basename(f_name))
            zip_file.write(f_name, arcname=arcname)
    data.seek(0)

    return send_file(
        data,
        mimetype="application/zip",
        as_attachment=True,
        attachment_filename="ocr_alto_xml_%s.zip" % task_info["result"]["task_id"]
    )

@frontend.app_template_filter('format_date')
def _jinja2_filter_format_date(date, fmt="%d.%m.%Y, %H:%M"):
    return date.strftime(fmt)

@frontend.app_template_filter('format_delta')
def _jinja2_filter_format_delta(delta):
    return delta.__str__()
