# -*- coding: utf-8 -*-

"""
Extract predefined processors information.
"""

import json
import copy
import subprocess

from flask import jsonify
from flask_restx import Resource

from ocrd_butler.api.restx import api

from ocrd_butler.config import Config

ocrd_config = Config()

processors_namespace = api.namespace(
    "processors",
    description="Get the processors known by our butler.")

PROCESSORS_CONFIG = {}

for package in ocrd_config.PROCESSORS:
    ocrd_tool = subprocess.check_output([package, "--dump-json"])
    PROCESSORS_CONFIG[package] = {"package": {"name": package}}
    PROCESSORS_CONFIG[package].update(json.loads(ocrd_tool))

PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()

# We prepare an usable action configuration from the config itself.
PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)
for name, config in PROCESSORS_ACTION.items():

    if "package" in config:
        del config["package"]

    parameters = {}
    if "parameters" in config:
        for p_name, p_values in config["parameters"].items():
            if "default" in p_values:
                parameters[p_name] = p_values["default"]
    config["parameters"] = parameters

    # Just take the first in-/output file group for now.
    # TODO: This is also connected to the choosen paramters.
    try:
        config["input_file_grp"] = config["input_file_grp"][0]
    except KeyError:
        pass

    # TODO: Move this fixed setting to a configuration like place. (tbi)
    if name == "ocrd-olena-binarize":
        config["output_file_grp"] = "OCR-D-IMG-BINPAGE"
    else:
        try:
            config["output_file_grp"] = config["output_file_grp"][0]
        except KeyError:
            pass

PROCESSORS_VIEW = []
for name, config in PROCESSORS_CONFIG.items():
    processor = {"name": name}
    the_config = copy.deepcopy(config)
    processor.update(the_config)
    PROCESSORS_VIEW.append(processor)


@processors_namespace.route("")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        """Returns the processor informations as JSON data."""
        return jsonify(PROCESSORS_VIEW)
