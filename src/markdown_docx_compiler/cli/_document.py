"""Document noun: create and validate commands."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from markdown_docx_compiler.cli._output import emit_success

if TYPE_CHECKING:
    pass

_EPILOG = """\
Reference — Supported markdown, front matter, and anchors:

  Run `mdc doc --help` for supported markdown features.
  Run `mdc doc create --help` for front matter keys.
"""

HELP_TOPIC_MARKDOWN = """\
# Supported Markdown

## Block features

- headings (h1-h6)
- paragraphs
- ordered and bullet lists, including nesting
- fenced code blocks
- blockquotes
- horizontal rules
- tables (pipe syntax)
- standalone images via ![alt](path)

## Inline features

- **bold**
- *italic*
- ~~strikethrough~~
- `inline code`
- [links](url)
- hard and soft line breaks

## Region tags

Place content into page headers, footers, or a doc header:

  <!-- docx:page_header.left -->
  <!-- docx:page_footer.right -->
  <!-- docx:doc_header.left -->

The tagged block is extracted into the region slot.

## Anchor tags

Tag a block for instance-level styling:

  <!-- docx:id=results-table -->

Reference the anchor in the sidecar `blocks:` section.
"""


def register_document_parser(noun_subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from markdown_docx_compiler.parser.front_matter import HELP_TOPIC as _FRONTMATTER

    noun_parser = noun_subparsers.add_parser(
        "document",
        aliases=["doc"],
        help="Compile and validate markdown documents",
        description="Compile and validate markdown documents.",
        epilog=HELP_TOPIC_MARKDOWN,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    noun_parser.set_defaults(noun_parser=noun_parser)
    verb_sub = noun_parser.add_subparsers(dest="verb")

    create_p = verb_sub.add_parser(
        "create",
        help="Compile markdown into styled DOCX",
        description="Compile a markdown file into a styled DOCX optimized for Google Docs import.",
        epilog=_FRONTMATTER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_p.add_argument("input", help="Input markdown file path")
    create_p.add_argument(
        "-o",
        "--output-file",
        help="Output DOCX file path (defaults to <input>.docx next to the markdown file)",
    )
    create_p.add_argument("--spec", help="Sidecar YAML path (auto-discovered if omitted)")
    create_p.set_defaults(handler=_handle_create, verb="create")

    validate_p = verb_sub.add_parser(
        "validate",
        help="Parse and resolve without writing the DOCX",
        description="Parse markdown, resolve sidecar, report results without writing a file.",
    )
    validate_p.add_argument("input", help="Input markdown file path")
    validate_p.add_argument("--spec", help="Sidecar YAML path (auto-discovered if omitted)")
    validate_p.set_defaults(handler=_handle_validate, verb="validate")


def _handle_create(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.compile import compile_markdown_file

    result = compile_markdown_file(
        input_path=args.input,
        output_path=args.output_file,
        spec_path=args.spec,
        dry_run=False,
    )
    emit_success(
        command="document create",
        data=result.to_dict(),
        human=f"Wrote {result.output_path}",
    )


def _handle_validate(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.compile import compile_markdown_file

    result = compile_markdown_file(
        input_path=args.input,
        output_path=None,
        spec_path=args.spec,
        dry_run=True,
    )
    data = result.to_dict()
    data["validation_only"] = True
    data["default_output_path"] = result.output_path
    emit_success(
        command="document validate",
        data=data,
        human=f"Valid — {result.block_count} blocks",
    )
