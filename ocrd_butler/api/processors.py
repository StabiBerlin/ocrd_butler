# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

import os
import json
import copy
import inspect

from flask import jsonify
from flask_restplus import Resource

from ocrd_butler.api.restplus import api
from ocrd_butler.util import camel_case_split

PROCESSORS_CONFIG = {}

DIRECT_SCRIPTS = [
    "../ocrd_all/ocrd_olena",
    "../ocrd_all/ocrd_tesserocr"
]
PROCESSOR_PACKAGES = [
    #"ocrd_tesserocr", # Segmentation fault while importing the package
    "ocrd_calamari",
    "ocrd_segment",
    "ocrd_ocropy",
    "ocrd_keraslm",
    "ocrd_kraken",
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
    with open(ocrd_tool_file) as fh:
        ocrd_tool = json.load(fh)

    if not os.path.exists(ocrd_tool_file):
        continue
    
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
    try:
        config["output_file_grp"] = config["output_file_grp"][0]
    except KeyError:
        pass

PROCESSORS_VIEW = []
for name, config in PROCESSORS_CONFIG.items():
    processor = {"name": name}
    the_config = copy.deepcopy(config)
    #del the_config["class"]
    processor.update(the_config)
    PROCESSORS_VIEW.append(processor)

ns = api.namespace("processors", description="The processors known by our butler.")

@ns.route("/processors")
class Processors(Resource):
    """Shows the processor configuration."""

    def get(self):
        return jsonify(PROCESSORS_VIEW)
