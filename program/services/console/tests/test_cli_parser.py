"""Tests for CLI argument parser."""

from __future__ import annotations

import pytest

from moneymaker_console import __version__
from moneymaker_console.cli.parser import build_cli_parser
from moneymaker_console.registry import CommandRegistry


@pytest.fixture()
def parser(registry):
    return build_cli_parser(registry)


class TestBuildCliParser:
    def test_returns_parser(self, parser):
        assert parser is not None
        assert parser.prog == "moneymaker"

    def test_version_in_description(self, parser):
        assert __version__ in parser.description

    def test_parse_category_subcmd(self, parser):
        args = parser.parse_args(["svc", "status"])
        assert args.category == "svc"
        assert args.subcmd == "status"

    def test_parse_with_json_flag(self, parser):
        args = parser.parse_args(["--json", "svc", "status"])
        assert args.json is True
        assert args.category == "svc"

    def test_parse_with_yes_flag(self, parser):
        args = parser.parse_args(["--yes", "svc", "status"])
        assert args.yes is True

    def test_parse_with_y_flag(self, parser):
        args = parser.parse_args(["-y", "svc", "status"])
        assert args.yes is True

    def test_no_category(self, parser):
        args = parser.parse_args([])
        assert args.category is None

    def test_category_only(self, parser):
        args = parser.parse_args(["svc"])
        assert args.category == "svc"
        assert args.subcmd == ""

    def test_extra_args(self, parser):
        args = parser.parse_args(["svc", "restart", "postgres"])
        assert args.category == "svc"
        assert args.subcmd == "restart"
        assert args.args == ["postgres"]

    def test_categories_from_registry(self, parser):
        # All registry categories should be valid subparser names
        args = parser.parse_args(["brain", "state"])
        assert args.category == "brain"

    def test_version_flag(self, parser):
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0
