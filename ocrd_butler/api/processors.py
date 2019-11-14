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

PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)
for name, config in PROCESSORS_ACTION.items():
    for tool_name, tool_config in config["tools"]:
        parameters = {}
        for p_name, p_values in tool_config["parameters"]:
            # TODO: Convert parameter definitions to inputs with
            #       defaults or predefined values from the config
            #       itself.
            pass
        tool_config["parameters"] = parameters

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
