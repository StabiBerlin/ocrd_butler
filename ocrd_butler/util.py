# -*- coding: utf-8 -*-

"""Utils module."""

import json
import os

def get_config_json(config_file=None):
    if config_file is None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        config_file_path = os.path.join(dir_path, "./config/config.json")
        config_file = os.path.abspath(config_file_path)
    try:
        with open(config_file) as config_handle:
            config_json = json.load(config_handle)
    except FileNotFoundError as exc:
        print ("Can't find configuration file '{}'. ({})".format(
            config_file,
            exc.__str__()))
    return config_json
