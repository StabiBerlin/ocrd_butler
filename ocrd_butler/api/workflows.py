# -*- coding: utf-8 -*-
# pylint: disable=no-member

""" Workflow api implementation.
"""

from collections import Mapping
from flask import (
    make_response,
    jsonify,
    request
)
from flask_restx import (
    Resource,
    marshal
)
import uuid
from ocrd_validators import ParameterValidator

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import workflow_model
from ocrd_butler.api.processors import (
    PROCESSORS_ACTION,
    PROCESSOR_NAMES,
    PROCESSORS_CONFIG
)
from ocrd_butler.database import db
from ocrd_butler.database.models import Workflow as db_model_Workflow
from responses import Response

workflow_namespace = api.namespace("workflows", description="Manage OCR-D processor workflows")


class WorkflowBase(Resource):
    """Base methods for workflows."""

    def validate_processor(self, processor):
        """ The OCR-D validator updates all parameters with default values. """
        if not isinstance(processor, Mapping):
            workflow_namespace.abort(400,
                f'Wrong parameter. Unknown processor "{processor}".')

        if processor["name"] not in PROCESSOR_NAMES:
            workflow_namespace.abort(
                400, f'Wrong parameter. Unknown processor "{processor["name"]}".')

        processor.update(PROCESSORS_ACTION[processor["name"]])

        validator = ParameterValidator(PROCESSORS_CONFIG[processor["name"]])
        if "parameters" not in processor:
            processor["parameters"] = {}

        report = validator.validate(processor["parameters"])

        if not report.is_valid:
            workflow_namespace.abort(
                400, f'Wrong parameter. '
                        f'Error(s) while validating parameters "{processor["parameters"]}" '
                        f'for processor "{processor["name"]}" -> "{str(report.errors)}".'
            )

        return processor

    def workflow_data(self, json_data):
        """ Validate and prepare workflow database input. """
        data = marshal(data=json_data, fields=workflow_model, skip_none=False)

        workflow = {
            "name": data["name"],
            "description": data["description"],
            "processors": []
        }

        if not data["processors"]:
            workflow_namespace.abort(400,
                f'Wrong parameter. Processors "{data["processors"]}" seems empty.')

        for processor in data["processors"]:
            validated_processor = self.validate_processor(processor)
            workflow["processors"].append(validated_processor)

        return workflow

@workflow_namespace.route("")
class Workflows(WorkflowBase):
    """ Add workflows and list all of it. """

    @api.doc(responses={201: "Created", 400: "Wrong parameter."})
    @api.expect(workflow_model, validate=True)
    def post(self):
        """ Add a new workflow.

        A workflow is a list of OCRD processors. By default every processor is used with its default values from its `ocrd-tool.json` or from fixed definitions in the butler, e.g. for the folders of the models. Its possible to overwrite these settings directly with given parameters.:
        [
            {
                "name": "ocrd-example"
            },
            {
                "name": "ocrd-example-2",
                "parameters": {
                    "model": "/data/example/models"
                }
            },
        ]
        """

        data = self.workflow_data(request.json)
        workflow = db_model_Workflow.add(**data)
        return make_response({
            "message": "Workflow created.",
            "uid": workflow.uid,
            "id": workflow.id,
        }, 201)

    @api.doc(responses={200: "Found"})
    def get(self):
        """ Get all workflows. """
        workflows = db_model_Workflow.get_all()
        results = [workflow.to_json() for workflow in workflows]
        return jsonify(results)


@workflow_namespace.route("/<string:workflow_id>")
class Workflow(WorkflowBase):
    """Getter, updater and remover for workflows."""

    @api.doc(responses={200: "Found", 404: "Not known workflow id."})
    def get(self, workflow_id):
        """ Get the workflow by given id. """
        workflow = db_model_Workflow.get(id=workflow_id)

        if workflow is None:
            workflow_namespace.abort(
                404, f"Can't find a workflow with the id \"{workflow_id}\".")
        return jsonify(workflow.to_json())

    @api.doc(responses={201: "Updated", 404: "Unknown workflow."})
    @api.expect(workflow_model)
    def put(self, workflow_id: str) -> Response:
        """ Update a workflow. """
        workflow = db_model_Workflow.get(id=workflow_id)
        if workflow is None:
            workflow_namespace.abort(
                404, f"Can't find a workflow with the id \"{workflow_id}\".")

        workflow_data = workflow.to_json()
        fields = workflow_data.keys()
        update_data = request.json
        for field in fields:
            if field in update_data:
                if field == 'processors':
                    processors = []
                    for processor in update_data["processors"]:
                        self.validate_processor(processor)
                        processors.append(processor)
                    setattr(workflow, field, processors)
                else:
                    setattr(workflow, field, update_data[field])
        db.session.commit()

        return jsonify({
            "message": "Workflow updated.",
            "id": workflow.id,
        })

    @api.doc(responses={200: "Deleted", 404: "Unknown workflow id."})
    def delete(self, workflow_id: str) -> Response:
        """ Delete the workflow by given id. """
        workflow = db_model_Workflow.get(id=workflow_id)

        if workflow is None:
            workflow_namespace.abort(
                404, f"Can't find a workflow with the id \"{workflow_id}\".")
        else:
            message = f"Delete workflow \"{workflow.name}({workflow.id})\""
            if db_model_Workflow.delete(id=workflow_id):
                message = f'{message}: success'
            else:
                message = f'{message}: failed!'

        return jsonify({
            "message": message
        })
