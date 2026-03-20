"""Inline-level rendering: text spans, bold, italic, links, code spans."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from docx.shared import Pt
from docx.text.run import Run

from markdown_docx_compiler.backend.docx.ooxml_helpers import add_hyperlink_run, rgb, set_all_fonts
from markdown_docx_compiler.models.document import (
    CodeSpan,
    EmphasisSpan,
    InlineNode,
    LineBreak,
    LinkSpan,
    StrikeSpan,
    StrongSpan,
    TextSpan,
)
from markdown_docx_compiler.models.style import FontStyle, LinkStyle


def render_inline_nodes(
    *,
    paragraph: Any,
    nodes: Iterable[InlineNode],
    font: FontStyle,
    link: LinkStyle | None = None,
    mono_font: str = "Consolas",
    bold: bool = False,
    italic: bool = False,
    strike: bool = False,
    hyperlink_url: str | None = None,
) -> None:
    """Render a sequence of inline nodes into a python-docx paragraph."""
    for node in nodes:
        _render_node(
            paragraph=paragraph,
            node=node,
            font=font,
            link=link,
            mono_font=mono_font,
            bold=bold,
            italic=italic,
            strike=strike,
            hyperlink_url=hyperlink_url,
        )


def _render_node(
    *,
    paragraph: Any,
    node: InlineNode,
    font: FontStyle,
    link: LinkStyle | None,
    mono_font: str,
    bold: bool,
    italic: bool,
    strike: bool,
    hyperlink_url: str | None,
) -> None:
    if isinstance(node, TextSpan):
        run = (
            add_hyperlink_run(paragraph, text=node.text, url=hyperlink_url)
            if hyperlink_url
            else paragraph.add_run(node.text)
        )
        _style_run(
            run,
            font=font,
            bold=bold,
            italic=italic,
            strike=strike,
            color_override=_link_color(font=font, link=link) if hyperlink_url else None,
        )
        if hyperlink_url:
            run.underline = _link_underline(link)
        return

    if isinstance(node, LineBreak):
        paragraph.add_run().add_break()
        return

    if isinstance(node, StrongSpan):
        render_inline_nodes(
            paragraph=paragraph,
            nodes=node.children,
            font=font,
            link=link,
            mono_font=mono_font,
            bold=True,
            italic=italic,
            strike=strike,
            hyperlink_url=hyperlink_url,
        )
        return

    if isinstance(node, EmphasisSpan):
        render_inline_nodes(
            paragraph=paragraph,
            nodes=node.children,
            font=font,
            link=link,
            mono_font=mono_font,
            bold=bold,
            italic=True,
            strike=strike,
            hyperlink_url=hyperlink_url,
        )
        return

    if isinstance(node, StrikeSpan):
        render_inline_nodes(
            paragraph=paragraph,
            nodes=node.children,
            font=font,
            link=link,
            mono_font=mono_font,
            bold=bold,
            italic=italic,
            strike=True,
            hyperlink_url=hyperlink_url,
        )
        return

    if isinstance(node, CodeSpan):
        run = (
            add_hyperlink_run(paragraph, text=node.text, url=hyperlink_url)
            if hyperlink_url
            else paragraph.add_run(node.text)
        )
        run.font.name = mono_font
        run.font.size = Pt(font.size or 9.5)
        run.font.color.rgb = rgb(_link_color(font=font, link=link) if hyperlink_url else (font.color or "111827"))
        set_all_fonts(run, mono_font)
        if hyperlink_url:
            run.underline = _link_underline(link)
        return

    if isinstance(node, LinkSpan):
        render_inline_nodes(
            paragraph=paragraph,
            nodes=node.children,
            font=font,
            link=link,
            mono_font=mono_font,
            bold=bold,
            italic=italic,
            strike=strike,
            hyperlink_url=node.url,
        )
        return


def _link_color(*, font: FontStyle, link: LinkStyle | None) -> str:
    return (link.color if link else None) or font.color or "2563EB"


def _link_underline(link: LinkStyle | None) -> bool:
    underline = link.underline if link else None
    return True if underline is None else underline


def _style_run(
    run: Run,
    *,
    font: FontStyle,
    bold: bool,
    italic: bool,
    strike: bool,
    color_override: str | None = None,
) -> None:
    """Apply font style to a run."""
    family = font.family or "Aptos"
    run.font.name = family
    run.font.size = Pt(font.size or 10.5)
    run.font.color.rgb = rgb(color_override or font.color or "111827")
    run.bold = bold or (font.bold is True)
    run.italic = italic or (font.italic is True)
    run.font.strike = strike or (font.strikethrough is True)
    if font.underline:
        run.underline = True
    if font.small_caps:
        run.font.small_caps = True
    if font.all_caps:
        run.font.all_caps = True
    set_all_fonts(run, family)


def _stringify_inline(nodes: Iterable[InlineNode]) -> str:
    """Flatten inline nodes to plain text."""
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, (TextSpan, CodeSpan)):
            parts.append(node.text)
        elif isinstance(node, LinkSpan):
            parts.append(_stringify_inline(node.children))
        elif isinstance(node, LineBreak):
            parts.append("\n")
        elif isinstance(node, (StrongSpan, EmphasisSpan, StrikeSpan)):
            parts.append(_stringify_inline(node.children))
    return "".join(parts)
