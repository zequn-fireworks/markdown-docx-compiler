"""Theme noun: list and show commands."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Any

from markdown_docx_compiler.cli._output import emit_success, is_json_mode


def register_theme_parser(noun_subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from markdown_docx_compiler.styles.themes import help_topic

    noun_parser = noun_subparsers.add_parser(
        "theme",
        help="Browse built-in themes and variants",
        description="Browse built-in themes and variants.",
        epilog=help_topic(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    noun_parser.set_defaults(noun_parser=noun_parser)
    verb_sub = noun_parser.add_subparsers(dest="verb")

    # --- list ---
    list_p = verb_sub.add_parser(
        "list",
        help="List themes and variants",
        description="List all built-in themes and their variant definitions.",
    )
    list_p.set_defaults(handler=_handle_list, verb="list")

    # --- show ---
    show_p = verb_sub.add_parser(
        "show",
        help="Show theme details",
        description="Show details for a specific theme.  Defaults to the built-in theme.",
    )
    show_p.add_argument("name", nargs="?", default="default", help="Theme name (default: default)")
    show_p.set_defaults(handler=_handle_show, verb="show")


def _handle_list(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.styles.themes import DEFAULT_THEME, _discover_templates

    themes: list[dict[str, Any]] = [_theme_summary(DEFAULT_THEME.name, DEFAULT_THEME)]

    for _name, (theme, _layout) in sorted(_discover_templates().items()):
        if not any(t["name"] == theme.name for t in themes):
            themes.append(_theme_summary(theme.name, theme))

    if is_json_mode():
        emit_success(command="theme list", data={"themes": themes})
    else:
        lines = ["Available themes:", ""]
        for t in themes:
            variants_str = ", ".join(f"{bt}({','.join(vs)})" for bt, vs in t["variants"].items())
            lines.append(f"  {t['name']:20s} font={t['font']}  variants: {variants_str}")
        print("\n".join(lines))


def _handle_show(args: argparse.Namespace) -> None:
    from markdown_docx_compiler.styles.themes import DEFAULT_THEME, _discover_templates

    theme = None
    if args.name == "default" or args.name == DEFAULT_THEME.name:
        theme = DEFAULT_THEME
    else:
        for _tpl_name, (t, _layout) in _discover_templates().items():
            if t.name == args.name:
                theme = t
                break

    if theme is None:
        from markdown_docx_compiler.cli._output import emit_error

        emit_error(
            command="theme show",
            code="UNKNOWN_THEME",
            message=f"Theme not found: {args.name}",
            hint="Run `mdc theme list` to see available themes.",
            context={"name": args.name},
        )
        return  # pragma: no cover

    doc = theme.document
    data: dict[str, Any] = {
        "name": theme.name,
        "document": asdict(doc),
        "variants": {bt: {vn: asdict(vs) for vn, vs in variants.items()} for bt, variants in theme.variants.items()},
    }
    if is_json_mode():
        emit_success(command="theme show", data=data)
    else:
        lines = [
            f"Theme: {theme.name}",
            f"  font:          {doc.font}",
            f"  mono_font:     {doc.mono_font}",
            f"  primary_color: #{doc.primary_color}" if doc.primary_color else "",
            f"  text_color:    #{doc.text_color}" if doc.text_color else "",
            f"  muted_color:   #{doc.muted_color}" if doc.muted_color else "",
            f"  border_color:  #{doc.border_color}" if doc.border_color else "",
        ]
        if theme.variants:
            lines.append("  variants:")
            for bt, variants in theme.variants.items():
                lines.append(f"    {bt}: {', '.join(variants.keys())}")
        print("\n".join(line for line in lines if line))


def _theme_summary(name: str, theme: Any) -> dict[str, Any]:
    return {
        "name": name,
        "font": theme.document.font,
        "mono_font": theme.document.mono_font,
        "variants": {bt: list(variants.keys()) for bt, variants in theme.variants.items()},
    }
