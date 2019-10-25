# -*- coding: utf-8 -*-

"""Fixtures for `ocrd_butler` package."""

import pytest
import os

from ocrd_butler.util import get_config_json

def pytest_configure(config):
    """Register additional pytest configuration."""
    # add the pytest.mark.celery() marker registration to the pytest.ini [markers] section
    # this prevents pytest 4.5 and newer from issueing a warning about an unknown marker
    # and shows helpful marker documentation when running pytest --markers.
    # see https://github.com/celery/celery/commit/6e91e94129f9a6fed8d00ad1ad8ce28c59d482ce
    # not needed anymore when we use celery>=4.4.x.
    config.addinivalue_line(
        "markers", "celery(**overrides): override celery configuration for a test case"
    )

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
