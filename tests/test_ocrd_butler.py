#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ocrd_butler` package."""

import pytest
from pytest import raises
from celery.exceptions import Retry

from unittest.mock import patch

from click.testing import CliRunner

from ocrd_butler import cli
from ocrd_butler.app import task_model
from ocrd_butler.tasks import create_task


@pytest.mark.celery(result_backend='redis://')
@patch('ocrd_butler.tasks.create_task')
def test_create_task(input):
    """ Test our create_task task. (need better wording...)
        This really creates the output.
    """
    task = create_task({
            "id": "PPN80041750X",
            "mets_url": "https://content.staatsbibliothek-berlin.de/dc/PPN80041750X.mets.xml",
            "file_grp": "DEFAULT",
            "tesseract_model": "deu"
        })
    assert task == {'task_id': 'PPN80041750X', 'status': 'Created'}

@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert 'ocrd_butler.cli.main' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert '--help  Show this message and exit.' in help_result.output
