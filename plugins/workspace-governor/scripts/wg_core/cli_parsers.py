from __future__ import annotations

import argparse

from .cli_parsers_assess import add_assess_parsers
from .cli_parsers_ops import add_ops_parsers
from .cli_parsers_publish import add_publish_parsers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace governor helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_assess_parsers(subparsers)
    add_ops_parsers(subparsers)
    add_publish_parsers(subparsers)
    subparsers.add_parser("validate", help="Validate local plugin registration and assets")
    return parser
