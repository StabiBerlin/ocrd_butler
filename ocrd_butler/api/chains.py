# -*- coding: utf-8 -*-

""" Chain api implementation.
"""

import json

from flask import jsonify, request
from flask_restx import (
    Resource,
    marshal
)
from ocrd_validators import ParameterValidator

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import chain_model
from ocrd_butler.api.processors import (
    PROCESSOR_NAMES,
    PROCESSORS_CONFIG
)
from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain

chain_namespace = api.namespace("chains", description="Manage OCR-D processor chains")


@chain_namespace.route("")
class ChainList(Resource):
    """ Add chains and list all of it. """

    @api.doc(responses={201: "Created", 400: "Wrong parameter."})
    @api.expect(chain_model)
    def post(self):
        """ Add a new chain. """

        data = marshal(data=request.json, fields=chain_model, skip_none=False)

        if data["parameters"] is None:
            data["parameters"] = {}

        # Should some checks be in the model itself?
        if data["processors"] is None:
            chain_namespace.abort(400, "Wrong parameter.",
                                  status="Missing processors for chain.", statusCode="400")

        for processor in data["processors"]:
            if processor not in PROCESSOR_NAMES:
                chain_namespace.abort(400, "Wrong parameter.",
                                      status="Unknown processor \"{}\".".format(processor),
                                      statusCode="400")

            # The OCR-D validator updates all parameters with default values.
            if processor not in data["parameters"].keys():
                data["parameters"][processor] = {}
            validator = ParameterValidator(PROCESSORS_CONFIG[processor])
            report = validator.validate(data["parameters"][processor])
            if not report.is_valid:
                chain_namespace.abort(
                    400, "Wrong parameter.",
                    status="Unknown parameter \"{0}\" for processor \"{1}\".".format(
                        data["parameters"][processor], processor),
                    statusCode="400")

        processors_serialized = json.dumps(data["processors"])
        parameters_serialized = json.dumps(data["parameters"])

        chain = db_model_Chain(data["name"], data["description"],
                               processors_serialized, parameters_serialized)
        db.session.add(chain)
        db.session.commit()

        return jsonify({
            "message": "Chain created.",
            "id": chain.id,
        })

    @api.doc(responses={200: "Found"})
    def get(self):
        """ Get all chains. """
        chains = db_model_Chain.query.all()
        results = [{
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "processors": json.loads(chain.processors),
            "parameters": json.loads(chain.parameters),
            } for chain in chains]
        return jsonify(results)



@chain_namespace.route("/<string:chain_id>")
class Chain(Resource):
    """Getter, updater and remover for chains."""

    @api.doc(responses={200: "Found", 404: "Not known chain id."})
    def get(self, chain_id):
        """ Get the chain by given id. """
        chain = db_model_Chain.query.filter_by(id=chain_id).first()

        if chain is None:
            chain_namespace.abort(
                404, "Wrong parameter",
                status="Can't find a chain with the id \"{0}\".".format(chain_id),
                statusCode="404")

        return jsonify({
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "processors": json.loads(chain.processors),
            "parameters": json.loads(chain.parameters),
        })

    def put(self, chain_id):
        """ Update the chain. """
        pass

    def delete(self, chain_id):
        """ Delete the chain by given id. """
        res = db_model_Chain.query.filter_by(id=chain_id)
        chain = res.first()
        message = "Deleted chain {0} ({1})".format(chain.name, chain.id)
        res.delete()
        db.session.commit()

        return jsonify({
            "message": message
        })
