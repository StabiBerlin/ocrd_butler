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

from ocrd_butler.util import host_url, flower_url


tasks_blueprint = Blueprint("tasks_blueprint", __name__)


@tasks_blueprint.app_template_filter('format_date')
def _jinja2_filter_format_date(date, fmt="%d.%m.%Y, %H:%M"):
    return date.strftime(fmt)


@tasks_blueprint.app_template_filter('format_delta')
def _jinja2_filter_format_delta(delta):
    return delta.__str__()


def task_information(worker_task_id):
    """
    Get information for the task based on its worker task id from flower service.
    """
    if worker_task_id is None:
        return None

    flower_base = flower_url(request)
    response = requests.get(f"{flower_base}/api/task/info/{worker_task_id}")
    if response.status_code == 404:
        current_app.logger.warning("Can't find task '{0}'".format(worker_task_id))
        return None
    try:
        task_info = json.loads(response.content)
    except json.decoder.JSONDecodeError as exc:
        current_app.logger.error(f"Can't read response for task '{worker_task_id}'. ({exc.__str__()})")
        return None

    task_info["ready"] = task_info["state"] == "SUCCESS"
    if task_info["result"] is not None:
        task_info["result"] = json.loads(task_info["result"].replace("'", '"'))

    return task_info


def current_tasks():
    """
    Collect and prepare the current tasks.
    """
    results = [
        {
            **task,
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
            },
        }
        for task in requests.get(f'{host_url(request)}api/tasks').json()
    ]

    cur_tasks = []

    for result in results:
        task = {**result}

        task_info = task_information(result.get('worker_task_id'))

        uid = result.get('uid')
        if task_info is not None and task_info["ready"]:
            task["result"].update({
                "page": f"/download/page/{uid}",
                "alto": f"/download/alto/{uid}",
                "txt": f"/download/txt/{uid}",
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
    workflow_id = SelectField('Workflow', validators=[
        DataRequired(message="Please choose a workflow.")])
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
        "default_file_grp": request.form.get("input_file_grp") or "DEFAULT",
        "workflow_id": request.form.get("workflow_id"),
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
    # new_task_form = NewTaskForm(meta={'csrf': False})
    new_task_form = NewTaskForm()
    new_task_form.workflow_id.choices = [
        (
            workflow.get('id'),
            workflow.get('name', workflow.get('id'))
        )
        for workflow in requests.get(
            f'{host_url(request)}api/workflows'
        ).json()
    ]

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
        flash(f"An error occured: {result['status']}")

    return redirect("/tasks", code=302)


@tasks_blueprint.route("/task/run/<int:task_id>")
def task_run(task_id):
    """Run the task with the given id."""
    # pylint: disable=broad-except
    response = requests.post(f"{host_url(request)}api/tasks/{task_id}/run")

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


def validate_and_wrap_response(
        response: Response,
        payload_field: str,
        **kwargs
) -> Response:
    """ Create a new response based on the given response's status.

    If it's ok, then a new response is being created from all passed keyword parameters,
    and the value of the given response's member with the name specified
    by the ``payload_field`` parameter als payload.

    If it is not (status anything but 200), then a redirect to path ``/tasks`` is being
    returned.
    """
    if response.status_code != 200:
        flash(
            "An error occured: {0}".format(
                json.loads(
                    response.content
                ).get('status')
            )
        )
        return redirect("/tasks", code=302)
    else:
        return Response(
            getattr(response, payload_field),
            **kwargs
        )


@tasks_blueprint.route("/download/txt/<string:task_id>")
def download_txt(task_id):
    """Define route to download the results as text."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_txt")

    return validate_and_wrap_response(
        response, 'text',
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

    return validate_and_wrap_response(
        response, 'content',
        mimetype="application/zip",
        headers={
            "Content-Disposition":
            f"attachment;filename=ocr_page_xml_{task_id}.zip"
        }
    )


@tasks_blueprint.route("/download/alto/<string:task_id>")
def download_alto_zip(task_id):
    """Define route to download the alto xml results as zip file."""
    response = requests.get(f"{host_url(request)}api/tasks/{task_id}/download_alto")

    return validate_and_wrap_response(
        response, 'content',
        mimetype="application/zip",
        headers={
            "Content-Disposition":
            f"attachment;filename=ocr_alto_{task_id}.zip"
        }
    )
