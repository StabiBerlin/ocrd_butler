# -*- coding: utf-8 -*-

"""Restx initialization."""

from flask import (
    current_app,
    jsonify,
)
from flask_restx import (
    Api,
    Resource,
)


api = Api(
    version="v1",
    title="ORC-D butler API",
    description="Friendly service to handle your daily OCR-D tasks.")


util_ns = api.namespace(
    "_util", description="Invoke utility functions"
)


@util_ns.route("/routes")
class Routes(Resource):
    @api.doc()
    def get(self):
        """ List available API endpoints.
        """
        routes = [
            {
                'path': rule.rule or '',
                'methods': sorted(rule.methods or {}),
            }
            for rule in current_app.url_map.iter_rules()
        ]
        return jsonify(
            {
                route['path']: ', '.join(route['methods'])
                for route in routes
            }
        )
