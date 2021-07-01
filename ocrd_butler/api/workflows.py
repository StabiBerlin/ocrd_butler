# -*- coding: utf-8 -*-
# pylint: disable=no-member

""" Workflow api implementation.
"""

from flask import (
    make_response,
    jsonify,
    request
)
from flask_restx import (
    Resource,
    marshal
)
from ocrd_validators import ParameterValidator

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import workflow_model
from ocrd_butler.api.processors import (
    PROCESSOR_NAMES,
    PROCESSORS_CONFIG
)
from ocrd_butler.database import db
from ocrd_butler.database.models import Workflow as db_model_Workflow

workflow_namespace = api.namespace("chains", description="Manage OCR-D processor workflows")


class WorkflowBase(Resource):
    """Base methods for workflows."""

    def workflow_data(self, json_data):
        """ Validate and prepare workflow input. """
        data = marshal(data=json_data, fields=workflow_model, skip_none=False)

        if data["parameters"] is None:
            data["parameters"] = {}

        # Should some checks be in the model itself?
        if data["processors"] is None:
            workflow_namespace.abort(
                400, "Wrong parameter.",
                status="Missing processors for workflow.",
                statusCode="400"
            )

        for processor in data["processors"]:
            if processor not in PROCESSOR_NAMES:
                workflow_namespace.abort(
                    400, "Wrong parameter.",
                    status="Unknown processor \"{}\".".format(processor),
                    statusCode="400")

            # The OCR-D validator updates all parameters with default values.
            if processor not in data["parameters"].keys():
                data["parameters"][processor] = {}
            validator = ParameterValidator(PROCESSORS_CONFIG[processor])
            report = validator.validate(data["parameters"][processor])
            if not report.is_valid:
                workflow_namespace.abort(
                    400, "Wrong parameter.",
                    status=(
                        "Error while validating parameters \"{0}\""
                        "for processor \"{1}\" -> \"{2}\"."
                    ).format(
                        data["parameters"][processor],
                        processor,
                        str(report.errors)
                    ),
                    statusCode="400"
                )

        return data


@workflow_namespace.route("")
class Workflows(WorkflowBase):
    """ Add workflows and list all of it. """

    @api.doc(responses={201: "Created", 400: "Wrong parameter."})
    @api.expect(workflow_model)
    def post(self):
        """ Add a new workflow. """

        data = self.workflow_data(request.json)
        workflow = db_model_Workflow.add(**data)

        return make_response({
            "message": "Workflow created.",
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
                404, "Wrong parameter",
                status="Can't find a workflow with the id \"{0}\".".format(workflow_id),
                statusCode="404")

        return jsonify(workflow.to_json())

    @api.doc(responses={201: "Updated", 404: "Unknown workflow."})
    @api.expect(workflow_model)
    def put(self, workflow_id):
        """ Update a workflow. """
        workflow = db_model_Workflow.get(id=workflow_id)
        if workflow is None:
            workflow_namespace.abort(
                404, "Wrong parameter",
                status="Can't find a workflow with the id \"{0}\".".format(
                    workflow_id),
                statusCode="404")

        fields = workflow.to_json().keys()
        for field in fields:
            if field in request.json:
                setattr(workflow, field, request.json[field])
        db.session.commit()

        return jsonify({
            "message": "Workflow updated.",
            "id": workflow.id,
        })

    @api.doc(responses={200: "Deleted", 404: "Unknown workflow."})
    def delete(self, workflow_id):
        """ Delete the workflow by given id. """
        workflow = db_model_Workflow.get(id=workflow_id)

        if workflow is None:
            workflow_namespace.abort(
                404, "Unknown workflow_id",
                status="Can't find a workflow with the id \"{0}\".".format(workflow_id),
                statusCode="404")
        else:
            message = "Delete workflow \"{0}({1})\"".format(workflow.name, workflow.id)
            if db_model_Workflow.delete(id=workflow_id):
                message = f'{message}: success'
            else:
                message = f'{message}: failed!'

        return jsonify({
            "message": message
        })
