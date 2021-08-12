# -*- coding: utf-8 -*-

"""
Extract predefined processors information.
"""

import copy

from flask import jsonify
from flask_restx import Resource

from ocrd_butler.api.restx import api
from ocrd_butler.util import logger
from ocrd_butler import config as ocrd_config


log = logger(__name__)

processors_namespace = api.namespace(
    "processors",
    description="Get the processors known by our butler.")

PROCESSORS_CONFIG = {
    package: {
        "package": {"name": package},
        **ocrd_config.processor_specs(package)
    }
    for package in ocrd_config.PROCESSORS
}

PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()

# We prepare usable action configurations from the config itself.
PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)

# We override some base settings of the processors.
for processor, settings in ocrd_config.PROCESSOR_SETTINGS.items():
    for key, value in settings.items():
        PROCESSORS_ACTION.get(
            processor, {}
        )[key] = value

for name, config in PROCESSORS_ACTION.items():
    if "package" in config:
        del config["package"]
    if "parameters" in config:
        del config["parameters"]
    # parameters = {}
    # if "parameters" in config:
    #     for p_name, p_values in config["parameters"].items():
    #         if "default" in p_values:
    #             parameters[p_name] = p_values["default"]
    # config["parameters"] = parameters

    # Just take the first in-/output file group for now.
    # TODO: This is also connected to the choosen paramters.
    for key in ["input_file_grp", "output_file_grp"]:
        config[key] = ''.join(config.get(key, [])[:1])


PROCESSORS_VIEW = []
for name, config in PROCESSORS_CONFIG.items():
    PROCESSORS_VIEW.append(
        {
            "name": name,
            **copy.deepcopy(config),
        }
    )

PROCESSORS_DEFAULTS = {}
for name, config in PROCESSORS_CONFIG.items():
    PROCESSORS_DEFAULTS[name] = config.get("parameters", {})

@processors_namespace.route("")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        """Returns the processor informations as JSON data."""
        return jsonify(PROCESSORS_VIEW)


@processors_namespace.route("/<string:name>")
class Processor(Resource):

    def get(self, name: str):
        """ Returns specifications for a single processor.
        """
        return jsonify(
            PROCESSORS_CONFIG.get(name, {})
        )
