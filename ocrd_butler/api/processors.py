# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

import copy
import inspect

from flask import jsonify
from flask_restplus import Resource

from ocrd_tesserocr.segment_region import TesserocrSegmentRegion
from ocrd_tesserocr.segment_line import TesserocrSegmentLine
from ocrd_tesserocr.segment_word import TesserocrSegmentWord
from ocrd_tesserocr.recognize import TesserocrRecognize

from ocrd_calamari.recognize import CalamariRecognize
from ocrd_calamari.config import OCRD_TOOL as ocrd_calamari_tool
from ocrd_calamari import cli as ocrd_calamari_cli

from ocrd_butler.api.restplus import api
from ocrd_butler.util import camel_case_split

PROCESSORS_CONFIG = {}

PROCESSOR_PACKAGES = [
    "ocrd_calamari",
    "ocrd_tesserocr"
]

for package in PROCESSOR_PACKAGES:
    module = __import__(package, fromlist=["config", "cli"])
    for name, config in module.config.OCRD_TOOL["tools"].items():
        last_name = name.split("-")[-1]
        for member in inspect.getmembers(module.cli):
            if last_name == camel_case_split(member[0])[-1].lower():
                PROCESSORS_CONFIG[member[0]] = {
                    "class": member[1],
                }
                PROCESSORS_CONFIG[member[0]].update(config)
                break

PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()

# We prepare an usable action configuration from the config itself.
PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)
for name, config in PROCESSORS_ACTION.items():
    parameters = {}
    if "parameters" in config:
        for p_name, p_values in config["parameters"].items():
            if "default" in p_values:
                parameters[p_name] = p_values["default"]
    config["parameters"] = parameters
    # Just take the first in-/output file group for now.
    # TODO: This is also connected to the choosen paramters.
    config["input_file_grp"] = config["input_file_grp"][0]
    config["output_file_grp"] = config["output_file_grp"][0]

PROCESSORS_VIEW = []
for name, config in PROCESSORS_CONFIG.items():
    processor = {"name": name}
    the_config = copy.deepcopy(config)
    del the_config["class"]
    processor.update(the_config)
    PROCESSORS_VIEW.append(processor)

ns = api.namespace("processors", description="The processors known by our butler.")

@ns.route("/processors")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        return jsonify(PROCESSORS_VIEW)
