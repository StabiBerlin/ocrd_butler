# -*- coding: utf-8 -*-

"""Tests for `ocrd_butler` package."""

import pytest
from click.testing import CliRunner
from ocrd_butler import cli


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert 'Run a shell in the app context.' in result.output
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert ' --help     Show this message and exit.' in help_result.output
