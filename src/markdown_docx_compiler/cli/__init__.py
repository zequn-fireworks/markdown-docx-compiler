"""CLI entry point for markdown-docx-compiler.

Commands follow ``mdc <noun> <verb> --args`` structure.
Run ``mdc --json`` for a machine-readable discovery payload.
Run ``mdc <noun> --help`` for detailed reference documentation.
"""

from __future__ import annotations

import argparse
import logging

import yaml

from markdown_docx_compiler import __version__
from markdown_docx_compiler.cli._discovery import build_discovery_payload
from markdown_docx_compiler.cli._document import register_document_parser
from markdown_docx_compiler.cli._output import emit_error, emit_success, set_json_mode
from markdown_docx_compiler.cli._spec import register_spec_parser
from markdown_docx_compiler.cli._template import register_template_parser
from markdown_docx_compiler.cli._theme import register_theme_parser

_TOP_LEVEL_DESCRIPTION = """\
Compile AI-authored markdown into polished .docx for Google Docs import.

Commands follow <noun> <verb> structure:

  mdc doc create report.md -o report.docx
  mdc doc create report.md --spec report.docx.yaml -o report.docx
  mdc doc validate report.md
  mdc spec show --for report.md --resolved
  mdc template list
  mdc theme show default

Abbreviations: document=doc, template=tpl

Use --json with any command for machine-readable output.
Use mdc --json (no noun) for a discovery payload listing all nouns and verbs.
Use mdc <noun> --help for detailed reference documentation.
"""


def main() -> None:
    """Parse CLI arguments and dispatch to noun-verb handlers."""
    parser = argparse.ArgumentParser(
        prog="mdc",
        description=_TOP_LEVEL_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    noun_subparsers = parser.add_subparsers(dest="noun")

    register_document_parser(noun_subparsers)
    register_spec_parser(noun_subparsers)
    register_template_parser(noun_subparsers)
    register_theme_parser(noun_subparsers)

    args = parser.parse_args()

    set_json_mode(args.json)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    # No noun: discovery payload (--json) or top-level help.
    if args.noun is None:
        if args.json:
            emit_success("discovery", build_discovery_payload())
        else:
            parser.print_help()
        return

    # Noun given but no verb: show that noun's help.
    handler = getattr(args, "handler", None)
    if handler is None:
        noun_parser: argparse.ArgumentParser = getattr(args, "noun_parser", parser)
        noun_parser.print_help()
        return

    # Dispatch to the verb handler with structured error wrapping.
    cmd = f"{args.noun} {getattr(args, 'verb', '')}".strip()
    try:
        handler(args)
    except SystemExit:
        raise
    except FileNotFoundError as exc:
        emit_error(
            command=cmd,
            code="FILE_NOT_FOUND",
            message=str(exc),
            hint="Check the file path. Use an absolute path or a path relative to the current directory.",
        )
    except yaml.YAMLError as exc:
        emit_error(
            command=cmd,
            code="INVALID_SIDECAR",
            message=str(exc),
            hint="Fix the YAML structure. Run `mdc spec --help` for the schema.",
        )
    except ValueError as exc:
        emit_error(
            command=cmd,
            code="INVALID_INPUT",
            message=str(exc),
            hint=f"Check the input. Run `mdc {args.noun} --help` for reference.",
        )
    except Exception as exc:
        emit_error(
            command=cmd,
            code="INTERNAL_ERROR",
            message=str(exc),
            hint="Unexpected error. Re-run with --verbose for debug output.",
            exit_code=2,
        )
