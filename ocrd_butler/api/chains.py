# -*- coding: utf-8 -*-

import json

from flask import jsonify, request

from flask_restplus import Resource

from ocrd_butler.api.restplus import api
from ocrd_butler.api.models import chain_model as api_model_chain
from ocrd_butler.api.processors import PROCESSOR_NAMES

from ocrd_butler.database import db
from ocrd_butler.database.models import Chain as db_model_Chain

ns = api.namespace("chains", description="Manage OCR-D processor chains")


@ns.route("/chain")
class ChainList(Resource):
    """ foobar """

    @api.doc(responses={ 201: "Created", 400: "Missing parameter", 400: "Wrong parameter" })
    @api.expect(api_model_chain)
    def post(self):
        """ foobar """

        name = request.json.get("name")
        description = request.json.get("description")
        processors = request.json.get("processors")

        for processor in processors:
            if processor not in PROCESSOR_NAMES:
                ns.abort(400, "Wrong parameter",
                             status = "Unknown processor \"{}\".".format(processor),
                             statusCode = "400")

        processors_serialized = json.dumps(processors)
        chain = db_model_Chain(name, description, processors_serialized)
        db.session.add(chain)
        db.session.commit()

        return jsonify({
            "message": "Chain created.",
            "id": chain.id,
        })

@ns.route("/chain/<string:id>")
class Chain(Resource):
    """Holds getter and updater for chains."""
    @api.doc(responses={ 200: "Created", 400: "Missing id" })
    def get(self, id):

        chain = db_model_Chain.query.filter_by(id=id).first()

        return jsonify({
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "processors": json.loads(chain.processors)
        })

    def put(self, id):
        pass

    def delete(self, id):
        pass



"""Our predefined processor chains.

   We create different chains with a specific names and a description how
   (or for what) useful they seem and set one chain as default.
   If no chain or chain name was given while creating the task the default
   one has to be used.
"""

tesserocr_chain = {
    "name": "Tesserocr Chain",
    "description": "Basic OCR creation via Tesseract with binarization",
    "processors": [
        {"TesserocrSegmentRegion": {}},
        {"TesserocrSegmentLine": {}},
        {"TesserocrSegmentWord": {}},
        {"TesserocrRecognize": {}}
    ]
}

processor_chains = [
    tesserocr_chain,
]

default_chain = tesserocr_chain
