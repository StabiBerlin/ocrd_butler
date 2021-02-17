"""
Routes for the compare view.
"""

import glob
import json
import os
from shutil import copyfile
import subprocess

from flask import (
    Blueprint,
    render_template,
    request
)

from flask_wtf import FlaskForm
from wtforms import (
    SubmitField,
    SelectField,
    SelectMultipleField,
)
from wtforms.validators import DataRequired
from wtforms.widgets import Select

from ocrd_butler.api.processors import PROCESSORS_ACTION
from ocrd_butler.frontend.tasks import task_information
from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task


compare_blueprint = Blueprint("compare_blueprint", __name__)


class CompareForm(FlaskForm):
    """Contact form."""
    task_from = SelectMultipleField(
        "Task from",
        validators=[DataRequired(message="Please choose a task to compare from.")],
        widget=Select(multiple=False))
    task_to = SelectField(
        "Task to",
        validators=[DataRequired(message="Please choose a task to compare to.")])
    submit = SubmitField('Compare tasks')


@compare_blueprint.route("/compare", methods=["GET"])
def compare():
    """
    Page for create a comparisation between two OCR text versions.
    """
    compare_form = CompareForm()
    task_choices = [
        (task.id, task.worker_task_id)
        for task in db_model_Task.get_all()
    ]
    compare_form.task_from.choices = task_choices
    compare_form.task_to.choices = task_choices[::]

    return render_template(
        "compare.html",
        form=compare_form)


@compare_blueprint.route('/compare', methods=['POST'])
def compare_results():
    """
    Compare two versions of OCR of the the same page with dinglehopper.

    1. We copy the files to compare in an own folder and use dinglehopper
       to produce html files.
       ▶ dinglehopper [OPTIONS] GT OCR [REPORT_PREFIX]
    2. We add the files as (fake) GT data to the mets files and use ocrd-dinglehopper.
       to get the results in the mets file.
       ▶ ocrd-dinglehopper -m mets.xml -I OCR-D-GT-PAGE,OCR-D-OCR-TESS -O OCR-D-OCR-TESS-EVAL
    3. We create an own mets file for this, copy there (fake) GT and (other) OCR and
       use also ocrd-dinglehopper.
    """

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
            os.path.basename(
                file.replace("FROM-", "TO-").replace(last_output_from, last_output_to)),
            "{}".format(count).zfill(4))
        try:
            subprocess.check_output([cmd], shell=True, cwd=dst_dir)
        except subprocess.CalledProcessError as exc:
            print('ERROR: {}'.format(exc.__str__()))

    results = []
    for count, file in enumerate(glob.glob("{}/RESULT-*.html".format(dst_dir))):
        results.append(open(file, 'r').read())

    return render_template(
        "compare_results.html",
        results=results)
