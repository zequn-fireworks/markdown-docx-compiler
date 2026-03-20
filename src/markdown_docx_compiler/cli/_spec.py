"""Spec noun: show, validate, and create commands."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from markdown_docx_compiler.cli._output import emit_error, emit_success, is_json_mode


def register_spec_parser(noun_subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from markdown_docx_compiler.help_text import HELP_TOPIC_SIDECAR

    noun_parser = noun_subparsers.add_parser(
        "spec",
        help="Manage sidecar configuration files",
        description="Manage sidecar configuration files.",
        epilog=HELP_TOPIC_SIDECAR,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    noun_parser.set_defaults(noun_parser=noun_parser)
    verb_sub = noun_parser.add_subparsers(dest="verb")

    # --- show ---
    show_p = verb_sub.add_parser(
        "show",
        help="Display sidecar content or resolved config",
        description=(
            "Display a sidecar file, or use --for to discover and display the sidecar "
            "for a markdown document.  Add --resolved to show the fully merged config."
        ),
    )
    show_p.add_argument("path", nargs="?", default=None, help="Sidecar YAML file path")
    show_p.add_argument(
        "--for",
        dest="for_doc",
        default=None,
        metavar="MARKDOWN_FILE",
        help="Discover sidecar for this markdown file",
    )
    show_p.add_argument(
        "--resolved",
        action="store_true",
        help="Show resolved document config and sidecar data (front matter is included when --for is used)",
    )
    show_p.set_defaults(handler=_handle_show, verb="show")

    # --- validate ---
    validate_p = verb_sub.add_parser(
        "validate",
        help="Check sidecar YAML validity",
        description="Validate a sidecar YAML file for structural correctness.",
    )
    validate_p.add_argument("path", nargs="?", default=None, help="Sidecar YAML file path")
    validate_p.add_argument(
        "--for",
        dest="for_doc",
        default=None,
        metavar="MARKDOWN_FILE",
        help="Discover sidecar for this markdown file",
    )
    validate_p.set_defaults(handler=_handle_validate, verb="validate")

    # --- create ---
    create_p = verb_sub.add_parser(
        "create",
        help="Scaffold a new sidecar YAML",
        description="Generate a starter sidecar YAML with annotated structure.",
    )
    create_p.add_argument("path", nargs="?", default=None, help="Output file path (default: stdout)")
    create_p.set_defaults(handler=_handle_create, verb="create")


def _resolve_spec_path(args: argparse.Namespace) -> Path:
    """Resolve the sidecar path from positional arg or --for flag."""
    if args.path and args.for_doc:
        emit_error(
            command=f"spec {args.verb}",
            code="INVALID_ARGS",
            message="Cannot use both a positional path and --for at the same time.",
            hint="Provide either a sidecar path or --for <markdown-file>, not both.",
        )
    if args.for_doc:
        from markdown_docx_compiler.compile import discover_sidecar_path

        md_path = Path(args.for_doc).resolve()
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        spec = discover_sidecar_path(md_path)
        if spec is None:
            emit_error(
                command=f"spec {args.verb}",
                code="NO_SPEC_FOUND",
                message=f"No sidecar found for {md_path.name}",
                hint="Create one with `mdc spec create` or pass a path explicitly.",
                context={"markdown_file": str(md_path)},
            )
        return spec  # type: ignore[return-value]
    if args.path:
        p = Path(args.path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Sidecar file not found: {p}")
        return p
    emit_error(
        command=f"spec {args.verb}",
        code="MISSING_ARG",
        message="No sidecar path provided.",
        hint="Provide a sidecar path or use --for <markdown-file> to auto-discover.",
    )
    raise AssertionError("unreachable")  # pragma: no cover


def _handle_show(args: argparse.Namespace) -> None:
    spec_path = _resolve_spec_path(args)

    if args.resolved:
        _show_resolved(spec_path, args)
        return

    from markdown_docx_compiler.models.loader import load_sidecar

    sidecar = load_sidecar(spec_path)
    data: dict[str, Any] = {
        "spec_path": str(spec_path),
        "sidecar": asdict(sidecar),
    }
    if is_json_mode():
        emit_success(command="spec show", data=data)
    else:
        print(f"# {spec_path.name}")
        print(spec_path.read_text(encoding="utf-8"))


def _show_resolved(spec_path: Path, args: argparse.Namespace) -> None:
    from markdown_docx_compiler.models.loader import load_sidecar
    from markdown_docx_compiler.parser.front_matter import extract_front_matter
    from markdown_docx_compiler.resolve.cascade import resolve_document_config

    sidecar = load_sidecar(spec_path)
    md_path = Path(args.for_doc).resolve() if args.for_doc else None
    front_matter: dict[str, Any] = {}

    if md_path and md_path.exists():
        raw = md_path.read_text(encoding="utf-8")
        front_matter, _ = extract_front_matter(raw)

    doc_config = resolve_document_config(
        sidecar=sidecar,
        front_matter=front_matter,
    )
    data: dict[str, Any] = {
        "spec_path": str(spec_path),
        "document_config": asdict(doc_config),
        "resolved_sidecar": asdict(sidecar),
    }
    if is_json_mode():
        emit_success(command="spec show", data=data)
    else:
        print(f"# Resolved config (spec={spec_path.name})")
        print(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _handle_validate(args: argparse.Namespace) -> None:
    spec_path = _resolve_spec_path(args)

    from markdown_docx_compiler.models.loader import load_sidecar

    sidecar = load_sidecar(spec_path)
    block_count = len(sidecar.defaults) + len(sidecar.blocks)
    data: dict[str, Any] = {
        "spec_path": str(spec_path),
        "valid": True,
        "inherits": sidecar.inherits,
        "defaults_count": len(sidecar.defaults),
        "blocks_count": len(sidecar.blocks),
    }
    emit_success(
        command="spec validate",
        data=data,
        human=f"Valid — {spec_path.name} ({block_count} rules)",
    )


_SCAFFOLD = """\
# Sidecar config for document styling.
# Run `mdc spec --help` for full reference.

# inherits: ../base.docx.yaml  # Inherit from another sidecar file

document:
  font: { family: Arial, size: 11, color: "333333" }
  # link: { color: "2563EB" }
  # page:
  #   margin: { top: 1.0, bottom: 0.8, left: 1.0, right: 1.0 }

# page_footer:
#   font: { size: 8, color: "666666" }

defaults:
  paragraph:
    spacing: { after: 6, line: 1.15 }
  table:
    table: { header_row: true }

# blocks:
#   my-anchor-id:
#     type: table
#     table: { columns: [3fr, 1fr, 1fr] }
"""


def _handle_create(args: argparse.Namespace) -> None:
    if args.path:
        out = Path(args.path)
        out.write_text(_SCAFFOLD, encoding="utf-8")
        emit_success(
            command="spec create",
            data={"path": str(out.resolve())},
            human=f"Created {out}",
        )
    else:
        emit_success(
            command="spec create",
            data={"scaffold": _SCAFFOLD},
            human=_SCAFFOLD,
        )
