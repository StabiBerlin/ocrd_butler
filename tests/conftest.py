# -*- coding: utf-8 -*-

"""Fixtures for `ocrd_butler` package."""

import pytest
import os

from ocrd_butler.util import get_config_json


@pytest.fixture
def config():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_file_path = os.path.join(dir_path, "./config.json")
    config_file = os.path.abspath(config_file_path)
    config = get_config_json(config_file=config_file)
    return config


@pytest.fixture
def tmp_dir(config):
    """ A temporary directory has to be clean for every scope. """
    try:
        os.rmdir(config["OCRD_BUTLER_RESULTS"])
    except FileNotFoundError:
        pass
    os.makedirs(config["OCRD_BUTLER_RESULTS"])
    return config["OCRD_BUTLER_RESULTS"]
