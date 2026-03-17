"""Document noun: create and validate commands."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from markdown_docx_compiler.cli._output import emit_success

if TYPE_CHECKING:
    pass

_EPILOG = """\
Reference — Supported markdown, front matter, and anchors:

  Run `mdc document --help` for supported markdown features.
  Run `mdc document create --help` for front matter keys.
"""


def register_document_parser(noun_subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from markdown_docx_compiler.parser.front_matter import HELP_TOPIC as _FRONTMATTER
    from markdown_docx_compiler.parser.markdown_parser import (
        HELP_TOPIC_ANCHORS as _ANCHORS,
    )
    from markdown_docx_compiler.parser.markdown_parser import (
        HELP_TOPIC_MARKDOWN as _MARKDOWN,
    )

    noun_parser = noun_subparsers.add_parser(
        "document",
        aliases=["doc"],
        help="Compile and validate markdown documents",
        description="Compile and validate markdown documents.",
        epilog=_MARKDOWN + "\n" + _ANCHORS,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    noun_parser.set_defaults(noun_parser=noun_parser)
    verb_sub = noun_parser.add_subparsers(dest="verb")

    # --- create ---
    create_p = verb_sub.add_parser(
        "create",
        help="Compile markdown into styled DOCX",
        description="Compile a markdown file into a styled DOCX optimized for Google Docs import.",
        epilog=_FRONTMATTER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_p.add_argument("input", help="Input markdown file path")
    create_p.add_argument("-o", "--output-file", help="Output DOCX file path")
    create_p.add_argument("--spec", help="Sidecar YAML path (auto-discovered if omitted)")
    create_p.add_argument("--template", help="Template name (e.g. fireworks-rca)")
    create_p.add_argument("--logo", help="Logo image path override")
    create_p.add_argument("--footer-left", help="Footer left text override")
    create_p.add_argument("--footer-center", help="Footer center text override")
    create_p.add_argument("--footer-right", help="Footer right text override")
    create_p.set_defaults(handler=_handle_create, verb="create")

    # --- validate ---
    validate_p = verb_sub.add_parser(
        "validate",
        help="Parse and resolve without writing the DOCX",
        description="Parse markdown, resolve sidecar and theme, report results without writing a file.",
    )
    validate_p.add_argument("input", help="Input markdown file path")
    validate_p.add_argument("--spec", help="Sidecar YAML path (auto-discovered if omitted)")
    validate_p.add_argument("--template", help="Template name (e.g. fireworks-rca)")
    validate_p.set_defaults(handler=_handle_validate, verb="validate")


def _handle_create(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.compiler import compile_markdown_file
    from markdown_docx_compiler.sidecar import DocumentConfig, FooterConfig

    overrides = DocumentConfig(
        logo_path=args.logo,
        footer=FooterConfig(
            left=args.footer_left,
            center=args.footer_center,
            right=args.footer_right,
        ),
    )
    result = compile_markdown_file(
        input_path=args.input,
        output_path=args.output_file,
        spec_path=args.spec,
        cli_overrides=overrides,
        template=args.template,
        dry_run=False,
    )
    emit_success(
        command="document create",
        data=result.to_dict(),
        human=f"Wrote {result.output_path}",
    )


def _handle_validate(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.compiler import compile_markdown_file

    result = compile_markdown_file(
        input_path=args.input,
        output_path=None,
        spec_path=args.spec,
        template=args.template,
        dry_run=True,
    )
    emit_success(
        command="document validate",
        data=result.to_dict(),
        human=f"Valid — {result.block_count} blocks, theme={result.theme}",
    )
