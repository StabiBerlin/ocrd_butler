# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

import os
import json
import copy

from flask import jsonify
from flask_restplus import Resource

from ocrd_butler.api.restplus import api


PROCESSORS_CONFIG = {}

DIRECT_SCRIPTS = [
    "/home/j23d/projects/ocrd/ocrd_all/ocrd_olena",
    "/home/j23d/projects/ocrd/ocrd_all/dinglehopper",
]


PROCESSOR_PACKAGES = [
    "ocrd_tesserocr",
    "ocrd_calamari",
    "ocrd_segment",
    "ocrd_keraslm",
    "ocrd_anybaseocr",
]


for package in DIRECT_SCRIPTS:
    ocrd_tool_file = os.path.abspath(os.path.join(package, "ocrd-tool.json"))

    if not os.path.exists(ocrd_tool_file):
        continue

    with open(ocrd_tool_file) as fh:
        ocrd_tool = json.load(fh)

    for name, config in ocrd_tool["tools"].items():
        PROCESSORS_CONFIG[name] = config


for package in PROCESSOR_PACKAGES:
    module = __import__(package, fromlist=["config", "cli"])
    m_path = module.__path__[0]
    ocrd_tool_file = os.path.abspath(os.path.join(m_path, "ocrd-tool.json"))
    if not os.path.exists(ocrd_tool_file):
        ocrd_tool_file = os.path.abspath(os.path.join(m_path, "..", "ocrd-tool.json"))
    if not os.path.exists(ocrd_tool_file):
        # ocrd_keraslm
        ocrd_tool_file = os.path.abspath(os.path.join(m_path, "wrapper", "ocrd-tool.json"))

    if not os.path.exists(ocrd_tool_file):
        print ("Can't find ocrd-tools.json from {0}, giving up.".format(package))
        continue

    with open(ocrd_tool_file) as fh:
        ocrd_tool = json.load(fh)


    for name, config in ocrd_tool["tools"].items():
        PROCESSORS_CONFIG[name] = config



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


NS = api.namespace("processors", description="The processors known by our butler.")


@NS.route("/processors")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        """Returns the processor informations as JSON data."""
        return jsonify(PROCESSORS_VIEW)
