# -*- coding: utf-8 -*-

"""Our chain configuration and the predefined processor chains."""

import os
import json
import copy

from flask import jsonify
from flask_restx import Resource

from ocrd_butler.api.restx import api

# TODO: This should be a loadable conf in JSON or similar
from ocrd_butler.config import Config

ocrd_config = Config()

processors_namespace = api.namespace(
    "processors",
    description="Get the processors known by our butler.")


PROCESSORS_CONFIG = {}


for package in ocrd_config.DIRECT_PROCESSOR_SCRIPTS:
    ocrd_tool_file = os.path.abspath(os.path.join(package, "ocrd-tool.json"))

    if not os.path.exists(ocrd_tool_file):
        raise ImportError(
            "Can't find ocrd-tools.json {0}, giving up.".format(ocrd_tool_file))

    with open(ocrd_tool_file) as fh:
        ocrd_tool = json.load(fh)

    package_information = {"package": {"name": os.path.basename(package)}}
    for name, value in ocrd_tool.items():
        if name == "tools":
            continue
        package_information["package"][name] = value

    for name, config in ocrd_tool["tools"].items():
        PROCESSORS_CONFIG[name] = config
        PROCESSORS_CONFIG[name].update(package_information)


for package in ocrd_config.PROCESSOR_PACKAGES:
    module = __import__(package, fromlist=["config", "cli"])
    m_path = module.__path__[0]

    ocrd_tool_file = os.path.abspath(os.path.join(m_path, "ocrd-tool.json"))
    if not os.path.exists(ocrd_tool_file):
        ocrd_tool_file = os.path.abspath(
            os.path.join(m_path, "..", "ocrd-tool.json"))
    if not os.path.exists(ocrd_tool_file):
        # ocrd_keraslm
        ocrd_tool_file = os.path.abspath(
            os.path.join(m_path, "wrapper", "ocrd-tool.json"))
    if not os.path.exists(ocrd_tool_file):
        raise ImportError(
            "Can't find ocrd-tools.json {0}, giving up.".format(ocrd_tool_file))

    with open(ocrd_tool_file) as fh:
        ocrd_tool = json.load(fh)

    package_information = {"package": {"name": package}}
    for name, value in ocrd_tool.items():
        if name == "tools":
            continue
        package_information["package"][name] = value

    for name, config in ocrd_tool["tools"].items():
        PROCESSORS_CONFIG[name] = config
        PROCESSORS_CONFIG[name].update(package_information)


PROCESSOR_NAMES = PROCESSORS_CONFIG.keys()


# We prepare an usable action configuration from the config itself.
PROCESSORS_ACTION = copy.deepcopy(PROCESSORS_CONFIG)
for name, config in PROCESSORS_ACTION.items():

    # TODO: check why not every processor has the package information
    if "package" in config:
        del config["package"]

    parameters = {}
    if "parameters" in config:
        for p_name, p_values in config["parameters"].items():
            if "default" in p_values:
                parameters[p_name] = p_values["default"]
    config["parameters"] = parameters

    # Just take the first in-/output file group for now.
    # TODO: This is also connected to the chosen parameters.
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
        """Returns the processor information as JSON data."""
        return jsonify(PROCESSORS_VIEW)
