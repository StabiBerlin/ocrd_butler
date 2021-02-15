"""
Routes for the tasks.
"""

from datetime import (
    datetime,
    timedelta
)
import json

import requests

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    Response
)

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    SelectField,
    TextAreaField
)
from wtforms.validators import (
    DataRequired,
    Length,
    URL
)

from ocrd_butler.database.models import Chain as db_model_Chain
from ocrd_butler.database.models import Task as db_model_Task
from ocrd_butler.util import host_url


tasks_blueprint = Blueprint("tasks_blueprint", __name__)


@tasks_blueprint.app_template_filter('format_date')
def _jinja2_filter_format_date(date, fmt="%d.%m.%Y, %H:%M"):
    return date.strftime(fmt)


@tasks_blueprint.app_template_filter('format_delta')
def _jinja2_filter_format_delta(delta):
    return delta.__str__()


def task_information(uid):
    """
    Get information for the task based on its uid.
    """
    if uid is None:
        return None

    response = requests.get(f"http://localhost:5555/api/task/info/{uid}")
    if response.status_code == 404:
        current_app.logger.warning("Can't find task '{0}'".format(uid))
        return None
    try:
        task_info = json.loads(response.content)
    except json.decoder.JSONDecodeError as exc:
        current_app.logger.error(f"Can't read response for task '{uid}'. ({exc.__str__()})")
        return None

    task_info["ready"] = task_info["state"] == "SUCCESS"
    if task_info["result"] is not None:
        task_info["result"] = json.loads(task_info["result"].replace("'", '"'))

    return task_info


def current_tasks():
    """
    Collect and prepare the current tasks.
    """
    results = db_model_Task.query.all()

    cur_tasks = []

    for result in results:
        chain = db_model_Chain.query.filter_by(id=result.chain_id).first()
        task = {
            "repr": result.__str__(),
            "description": result.description,
            "id": result.id,
            "uid": result.uid,
            "src": result.src,
            "default_file_grp": result.default_file_grp,
            "chain": chain,
            "parameters": result.parameters,
            "worker_task_id": result.worker_task_id,
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

        task_info = task_information(result.worker_task_id)

        if task_info is not None and task_info["ready"]:
            task["result"].update({
                "page": f"/download/page/{result.worker_task_id}",
                "alto": f"/download/alto/{result.worker_task_id}",
                "txt": f"/download/txt/{result.worker_task_id}",
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

        # A bit hacky, but for devs on localhost.
        flower_host_url = request.host_url.replace("5000", "5555")
        flower_path = "flower/" if "localhost:5000" not in request.host_url else ""
        task["flower_url"] = f"{flower_host_url}{flower_path}task/{task['worker_task_id']}"

        cur_tasks.append(task)

    return cur_tasks


class NewTaskForm(FlaskForm):
    """New task form."""
    task_description = StringField("Task description", [
        DataRequired(),
        Length(min=4, message=("The task has to be at least 4 letters."))])
    src = StringField("Source (METS)", validators=[
        DataRequired(message="Please enter an URL to a METS file."),
        URL(message="Please enter a valid URL to a METS file.")])
    input_file_grp = StringField("Input file group (defaults to 'DEFAULT')")
    chain_id = SelectField('Chain', validators=[
        DataRequired(message="Please choose a chain.")])
    parameter = TextAreaField('Parameters')
    submit = SubmitField('Create new task')


@tasks_blueprint.route("/new-task", methods=['POST'])
def new_task():
    """
    Create a new task from the data given in the form.

    TODO: Adjust task model works_id => id!
    """
    # pylint: disable=broad-except
    parameters = request.form.get("parameter")

    if parameters:
        parameters = json.loads(parameters)
    else:
        parameters = {}

    data = json.dumps({
        "description": request.form.get("task_description"),
        "src": request.form.get("src"),
        "file_grp": request.form.get("input_file_grp") or "DEFAULT",
        "chain_id": request.form.get("chain_id"),
        "parameters": parameters
    })
    headers = {"Content-Type": "application/json"}
    response = requests.post("{}api/tasks".format(host_url(request)),
                             data=data, headers=headers)

    if response.status_code == 201:
        flash("New task created.")
    else:
        try:
            result = response.json()
            flash("Can't create new task. Status {0}, Error '{1}': '{2}'.".format(
                result["statusCode"], result["message"], result["status"]))
        except Exception as exc:
            flash(f"Exception while displaying error message in new_task. Exc: {exc.__str__()}."
                  " Is the proxy active?")

    return redirect("/tasks", code=302)


@tasks_blueprint.route('/tasks', methods=['GET'])
def tasks():
    """Define the page presenting the created tasks."""
    # new_task_form = NewTaskForm(csrf_enabled=False)
    new_task_form = NewTaskForm()
    chains = db_model_Chain.query.all()
    new_task_form.chain_id.choices = [(chain.id, chain.name) for chain in chains]

    return render_template(
        "tasks.html",
        tasks=current_tasks(),
        form=new_task_form)


@tasks_blueprint.route("/task/delete/<int:task_id>")
def task_delete(task_id):
    """Delete the task with the given id."""
    response = requests.delete(f"{host_url(request)}api/tasks/{task_id}")

    if response.status_code in (200, 201):
        flash(f"Task {task_id} deleted.")
    else:
        result = json.loads(response.content)
        flash("An error occured: {0}".format(result.status))

    return redirect("/tasks", code=302)


@tasks_blueprint.route("/task/run/<int:task_id>")
def task_run(task_id):
    """Run the task with the given id."""
    # pylint: disable=broad-except
    response = requests.post(f"host_url(request)api/tasks/{task_id}/run")

    if response.status_code in (200, 201):
        flash(f"Task {task_id} started.")
    else:
        try:
            result = json.loads(response.content)
            flash(f"An error occured: {result['status']}")
        except Exception as exc:
            result = response.content
            flash(f"An error occured: {result}. (Exception: {exc.__str__()})")

    return redirect("/tasks", code=302)


@tasks_blueprint.route("/download/txt/<string:task_id>")
def download_txt(task_id):
    """Define route to download the results as text."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_txt")

    if response.status_code != 200:
        result = json.loads(response.content)
        flash("An error occured: {0}".format(result.status))
        return redirect("/tasks", code=302)

    return Response(
        response.text,
        mimetype="text/txt",
        headers={
            "Content-Disposition":
            f"attachment;filename=fulltext_{task_id}.txt"
        }
    )


@tasks_blueprint.route("/download/page/<string:task_id>")
def download_page_zip(task_id):
    """Define route to download the page xml results as zip file."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_page")

    if response.status_code != 200:
        result = json.loads(response.content)
        flash(f"An error occured: {result.status}")
        return redirect("/tasks", code=302)

    return Response(
        response.data,
        mimetype="application/zip",
        headers={
            "Content-Disposition":
            f"attachment;filename=ocr_page_xml_{task_id}.zip"
        }
    )

@tasks_blueprint.route("/download/pageviewer/<string:task_id>")
def download_pageviewer_zip(task_id):
    """Define route to download the page xml results as zip file."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_pageviewer")

    if response.status_code != 200:
        result = json.loads(response.content)
        flash(f"An error occured: {result.status}")
        return redirect("/tasks", code=302)

    return Response(
        response.data,
        mimetype="application/zip",
        headers={
            "Content-Disposition":
            f"attachment;filename=ocr_pageviewer_{task_id}.zip"
        }
    )

@tasks_blueprint.route("/download/alto/<string:task_id>")
def download_alto_zip(task_id):
    """Define route to download the alto xml results as zip file."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_pageviewer")

    if response.status_code != 200:
        result = json.loads(response.content)
        flash(f"An error occured: {result.status}")
        return redirect("/tasks", code=302)

    return Response(
        response.data,
        mimetype="application/zip",
        headers={
            "Content-Disposition":
            f"attachment;filename=ocr_alto_{task_id}.zip"
        }
    )
