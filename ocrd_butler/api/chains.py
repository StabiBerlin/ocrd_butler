# -*- coding: utf-8 -*-

import json

from flask import jsonify, request

from flask_restx import Resource

from ocrd_butler.api.restx import api
from ocrd_butler.api.models import chain_model as api_model_chain
from ocrd_butler.api.processors import PROCESSOR_NAMES

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain

NS = api.namespace("chains", description="Manage OCR-D processor chains")


class ChainList(Resource):
    """ Add chains and list all of it. """

    @NS.route("/chains")
    @api.doc(responses={ 201: "Created", 400: "Missing parameter", 400: "Wrong parameter" })
    @api.expect(api_model_chain)
    def post(self):
        """ Add a new chain. """

        name = request.json.get("name")
        description = request.json.get("description")
        processors = request.json.get("processors")

        for processor in processors:
            if processor not in PROCESSOR_NAMES:
                NS.abort(400, "Wrong parameter",
                             status="Unknown processor \"{}\".".format(processor),
                             statusCode="400")

        processors_serialized = json.dumps(processors)
        chain = db_model_Chain(name, description, processors_serialized)
        db.session.add(chain)
        db.session.commit()

        return jsonify({
            "message": "Chain created.",
            "id": chain.id,
        })

@NS.route("/chain/<string:id>")
class Chain(Resource):
    """Getter and updater for chains."""
    @api.doc(responses={ 200: "Found", 400: "Missing id" })
    def get(self, id):

        chain = db_model_Chain.query.filter_by(id=id).first()

        if chain is None:
            return jsonify({
                "message": "Can't find a chain with the id '{0}'.".format(id)
            })

        return jsonify({
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "processors": json.loads(chain.processors)
        })

    def put(self, id):
        pass

    def delete(self, id):
        res = db_model_Chain.query.filter_by(id=id)
        chain = res.first()
        message = "Deleted chain {0} ({1})".format(chain.name, chain.id)
        res.delete()
        db.session.commit()

        return jsonify({
            "message": message
        })
