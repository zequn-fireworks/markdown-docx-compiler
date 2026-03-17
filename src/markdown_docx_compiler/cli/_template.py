"""Template noun: list and show commands."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any

from markdown_docx_compiler.cli._output import emit_error, emit_success, is_json_mode


def register_template_parser(noun_subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from markdown_docx_compiler.styles.themes import templates_help_topic

    noun_parser = noun_subparsers.add_parser(
        "template",
        aliases=["tpl"],
        help="Browse installable template packages",
        description="Browse installable template packages.",
        epilog=templates_help_topic(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    noun_parser.set_defaults(noun_parser=noun_parser)
    verb_sub = noun_parser.add_subparsers(dest="verb")

    # --- list ---
    list_p = verb_sub.add_parser(
        "list",
        help="List installed templates",
        description="List all installed template packages.",
    )
    list_p.set_defaults(handler=_handle_list, verb="list")

    # --- show ---
    show_p = verb_sub.add_parser(
        "show",
        help="Show template details",
        description="Show details for a specific installed template.",
    )
    show_p.add_argument("name", help="Template name (e.g. fireworks, fireworks-rca)")
    show_p.set_defaults(handler=_handle_show, verb="show")


def _handle_list(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.styles.themes import DEFAULT_THEME, _discover_templates

    templates = _discover_templates()
    entries: list[dict[str, Any]] = [
        {
            "name": "default",
            "brand": DEFAULT_THEME.name,
            "font": DEFAULT_THEME.document.font,
            "builtin": True,
        }
    ]
    for name, (theme, _layout) in sorted(templates.items()):
        entries.append(
            {
                "name": name,
                "brand": theme.name,
                "font": theme.document.font,
                "builtin": False,
            }
        )

    if is_json_mode():
        emit_success(command="template list", data={"templates": entries})
    else:
        lines = ["Installed templates:", ""]
        for e in entries:
            tag = " (built-in)" if e["builtin"] else ""
            lines.append(f"  {e['name']:30s} brand={e['brand']}, font={e['font']}{tag}")
        if len(entries) == 1:
            lines.append("")
            lines.append("  Install more: uv add markdown-docx-compiler[templates]")
        print("\n".join(lines))


def _handle_show(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.styles.themes import get_template

    result = get_template(args.name)
    if result is None:
        emit_error(
            command="template show",
            code="UNKNOWN_TEMPLATE",
            message=f"Template not found: {args.name}",
            hint="Run `mdc template list` to see available templates.",
            context={"name": args.name},
        )
        return  # pragma: no cover (emit_error raises SystemExit)

    theme, layout = result
    data: dict[str, Any] = {
        "name": args.name,
        "brand": theme.name,
        "document": asdict(theme.document),
        "variants": {bt: list(variants.keys()) for bt, variants in theme.variants.items()},
        "layout": asdict(layout),
    }
    if is_json_mode():
        emit_success(command="template show", data=data)
    else:
        doc = theme.document
        lines = [
            f"Template: {args.name}",
            f"  brand:         {theme.name}",
            f"  font:          {doc.font}",
            f"  mono_font:     {doc.mono_font}",
            f"  primary_color: #{doc.primary_color}" if doc.primary_color else "",
            f"  text_color:    #{doc.text_color}" if doc.text_color else "",
        ]
        if theme.variants:
            lines.append("  variants:")
            for bt, variants in theme.variants.items():
                lines.append(f"    {bt}: {', '.join(variants.keys())}")
        print("\n".join(line for line in lines if line))
