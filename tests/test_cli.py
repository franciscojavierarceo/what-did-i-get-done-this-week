"""
Tests for the CLI interface
"""

import pytest
from click.testing import CliRunner
from what_did_i_get_done_this_week.cli import cli


def test_cli_help():
    """Test that CLI help works"""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "What Did I Get Done This Week?" in result.output


def test_generate_help():
    """Test generate command help"""
    runner = CliRunner()
    result = runner.invoke(cli, ['generate', '--help'])
    assert result.exit_code == 0
    assert "Generate a weekly review report" in result.output


def test_setup_help():
    """Test setup command help"""
    runner = CliRunner()
    result = runner.invoke(cli, ['setup', '--help'])
    assert result.exit_code == 0
    assert "Interactive setup and configuration" in result.output


def test_status_help():
    """Test status command help"""
    runner = CliRunner()
    result = runner.invoke(cli, ['status', '--help'])
    assert result.exit_code == 0
    assert "Show current configuration" in result.output