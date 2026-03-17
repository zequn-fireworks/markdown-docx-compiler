"""Sidecar config models and loading helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from markdown_docx_compiler._util import as_bool, as_dict, as_float, as_int, as_list, as_list_of_str, as_str

HELP_TOPIC = """\
# Sidecar Config

The sidecar is a YAML file that controls layout and styling beyond what front
matter provides.

## Auto-discovery

Place the sidecar next to the markdown file.  The compiler checks in order:

  1. <name>.docx.yaml
  2. <name>.docx.yml
  3. <name>.docspec.yaml
  4. <name>.docspec.yml

Or pass explicitly: mdc document create report.md --spec custom.yaml

## Structure

  template:   Optional installed template name (e.g. fireworks-rca)
  document:   Document-level config (footer, margins, fonts, colors)
  defaults:   Per-block-type default styles
  selectors:  Rules that match blocks by criteria and apply styles
  blocks:     Anchor-specific block overrides keyed by anchor ID

## Templates

Use an installed template as a starting point so you only specify overrides:

  template: fireworks-rca

  document:
    footer:
      center: "2026-03-16"

  blocks:
    results-table:
      columns: [3fr, 1fr, 1fr]

See `mdc template list` for available templates or `mdc template --help` for install instructions.

## Document section

  document:
    footer:
      left: "Company  |  Confidential"
      center: "2026-03-16"
      right: Draft
      show_page_numbers: true
    margin:
      top_inches: 1.0
      bottom_inches: 0.8

## Defaults section

Set default styles per block type:

  defaults:
    paragraph:
      variant: body
    table:
      variant: standard
      width: full

Block types: paragraph, table, code, blockquote, list, image, heading

## Blocks section

Target specific blocks by anchor ID (see `mdc document --help` for anchor syntax):

  blocks:
    results-table:
      variant: benchmark
      columns: [3fr, 1fr, 1fr]

## Block style properties

  variant            str     Named variant (e.g. "lead", "benchmark")
  width              str     Width mode (e.g. "full")
  columns            list    Column width ratios (e.g. [3fr, 1fr, 1fr])
  alignments         list    Column alignments
  font_size          float   Font size in points
  bold               bool    Bold text
  italic             bool    Italic text
  color              str     Hex text color without #
  background_color   str     Hex background color without #
  border_color       str     Hex border color without #
  line_spacing       float   Line spacing multiplier
  space_before       float   Space before block in points
  space_after        float   Space after block in points
  page_break_before  bool    Insert page break before this block

## Resolution order

Styles cascade (later wins):

  1. Template brand defaults (fonts, colors, variants)
  2. Template layout defaults (margins, footer, block defaults)
  3. Sidecar overrides (block-type defaults, selectors, anchor blocks)
  4. Front matter overrides
  5. CLI flag overrides
"""


@dataclass(frozen=True)
class FooterConfig:
    left: str | None = None
    center: str | None = None
    right: str | None = None
    show_page_numbers: bool | None = None


@dataclass(frozen=True)
class MarginConfig:
    top_inches: float | None = None
    bottom_inches: float | None = None
    left_inches: float | None = None
    right_inches: float | None = None


@dataclass(frozen=True)
class DocumentConfig:
    theme: str | None = None
    title: str | None = None
    logo_path: str | None = None
    font: str | None = None
    mono_font: str | None = None
    primary_color: str | None = None
    text_color: str | None = None
    muted_color: str | None = None
    border_color: str | None = None
    page_width_inches: float | None = None
    margin: MarginConfig = field(default_factory=MarginConfig)
    footer: FooterConfig = field(default_factory=FooterConfig)


@dataclass(frozen=True)
class BlockStyle:
    variant: str | None = None
    width: str | None = None
    columns: list[str] | None = None
    alignments: list[str] | None = None
    font_size: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    color: str | None = None
    background_color: str | None = None
    border_color: str | None = None
    line_spacing: float | None = None
    space_before: float | None = None
    space_after: float | None = None
    page_break_before: bool | None = None


@dataclass(frozen=True)
class SelectorMatch:
    type: str | None = None
    heading: str | None = None
    index: int | None = None
    anchor: str | None = None
    column_count: int | None = None


@dataclass(frozen=True)
class SelectorRule:
    match: SelectorMatch
    apply: BlockStyle


@dataclass(frozen=True)
class SidecarConfig:
    template: str | None = None
    document: DocumentConfig = field(default_factory=DocumentConfig)
    defaults: dict[str, BlockStyle] = field(default_factory=dict)
    selectors: list[SelectorRule] = field(default_factory=list)
    blocks: dict[str, BlockStyle] = field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Sidecar config must be a mapping: {path}")
    return payload


def _margin_from_dict(data: dict[str, Any] | None) -> MarginConfig:
    data = data or {}
    return MarginConfig(
        top_inches=as_float(data.get("top_inches") or data.get("top")),
        bottom_inches=as_float(data.get("bottom_inches") or data.get("bottom")),
        left_inches=as_float(data.get("left_inches") or data.get("left")),
        right_inches=as_float(data.get("right_inches") or data.get("right")),
    )


def _footer_from_dict(data: dict[str, Any] | None) -> FooterConfig:
    data = data or {}
    return FooterConfig(
        left=as_str(data.get("left")),
        center=as_str(data.get("center")),
        right=as_str(data.get("right")),
        show_page_numbers=as_bool(data.get("show_page_numbers")),
    )


def _document_from_dict(data: dict[str, Any] | None) -> DocumentConfig:
    data = data or {}
    return DocumentConfig(
        title=as_str(data.get("title")),
        logo_path=as_str(data.get("logo_path")),
        font=as_str(data.get("font")),
        mono_font=as_str(data.get("mono_font")),
        primary_color=as_str(data.get("primary_color")),
        text_color=as_str(data.get("text_color")),
        muted_color=as_str(data.get("muted_color")),
        border_color=as_str(data.get("border_color")),
        page_width_inches=as_float(data.get("page_width_inches")),
        margin=_margin_from_dict(as_dict(data.get("margin"))),
        footer=_footer_from_dict(as_dict(data.get("footer"))),
    )


def _block_style_from_dict(data: dict[str, Any] | None) -> BlockStyle:
    data = data or {}
    return BlockStyle(
        variant=as_str(data.get("variant")),
        width=as_str(data.get("width")),
        columns=as_list_of_str(data.get("columns")),
        alignments=as_list_of_str(data.get("alignments")),
        font_size=as_float(data.get("font_size")),
        bold=as_bool(data.get("bold")),
        italic=as_bool(data.get("italic")),
        color=as_str(data.get("color")),
        background_color=as_str(data.get("background_color")),
        border_color=as_str(data.get("border_color")),
        line_spacing=as_float(data.get("line_spacing")),
        space_before=as_float(data.get("space_before")),
        space_after=as_float(data.get("space_after")),
        page_break_before=as_bool(data.get("page_break_before")),
    )


def _selector_from_dict(data: dict[str, Any] | None) -> SelectorMatch:
    data = data or {}
    return SelectorMatch(
        type=as_str(data.get("type")),
        heading=as_str(data.get("heading")),
        index=as_int(data.get("index")),
        anchor=as_str(data.get("anchor")),
        column_count=as_int(data.get("column_count")),
    )


def _parse_sidecar_payload(payload: dict[str, Any]) -> SidecarConfig:
    """Parse a sidecar-shaped dict into a SidecarConfig."""
    defaults = {key: _block_style_from_dict(as_dict(value)) for key, value in as_dict(payload.get("defaults")).items()}
    blocks = {key: _block_style_from_dict(as_dict(value)) for key, value in as_dict(payload.get("blocks")).items()}
    selectors = []
    for item in as_list(payload.get("selectors")):
        if not isinstance(item, dict):
            continue
        selectors.append(
            SelectorRule(
                match=_selector_from_dict(as_dict(item.get("match"))),
                apply=_block_style_from_dict(as_dict(item.get("apply"))),
            )
        )

    return SidecarConfig(
        template=as_str(payload.get("template")),
        document=_document_from_dict(as_dict(payload.get("document"))),
        defaults=defaults,
        selectors=selectors,
        blocks=blocks,
    )


def load_sidecar(path: Path | None) -> SidecarConfig:
    """Load sidecar config or return defaults."""
    if path is None or not path.exists():
        return SidecarConfig()

    payload = _read_yaml(path=path)
    return _parse_sidecar_payload(payload)


def merge_document_config(base: DocumentConfig, override: DocumentConfig) -> DocumentConfig:
    """Overlay non-null values from *override* onto *base*."""
    merged_margin = replace(
        base.margin,
        top_inches=override.margin.top_inches if override.margin.top_inches is not None else base.margin.top_inches,
        bottom_inches=(
            override.margin.bottom_inches if override.margin.bottom_inches is not None else base.margin.bottom_inches
        ),
        left_inches=override.margin.left_inches if override.margin.left_inches is not None else base.margin.left_inches,
        right_inches=(
            override.margin.right_inches if override.margin.right_inches is not None else base.margin.right_inches
        ),
    )
    merged_footer = replace(
        base.footer,
        left=override.footer.left if override.footer.left is not None else base.footer.left,
        center=override.footer.center if override.footer.center is not None else base.footer.center,
        right=override.footer.right if override.footer.right is not None else base.footer.right,
        show_page_numbers=(
            override.footer.show_page_numbers
            if override.footer.show_page_numbers is not None
            else base.footer.show_page_numbers
        ),
    )
    return DocumentConfig(
        theme=override.theme or base.theme,
        title=override.title or base.title,
        logo_path=override.logo_path or base.logo_path,
        font=override.font or base.font,
        mono_font=override.mono_font or base.mono_font,
        primary_color=override.primary_color or base.primary_color,
        text_color=override.text_color or base.text_color,
        muted_color=override.muted_color or base.muted_color,
        border_color=override.border_color or base.border_color,
        page_width_inches=(
            override.page_width_inches if override.page_width_inches is not None else base.page_width_inches
        ),
        margin=merged_margin,
        footer=merged_footer,
    )


def merge_block_style(base: BlockStyle, override: BlockStyle) -> BlockStyle:
    """Overlay non-null values from *override* onto *base*."""
    values = asdict(base)
    for key, value in asdict(override).items():
        if value is not None:
            values[key] = value
    return BlockStyle(**values)


def merge_sidecar_config(base: SidecarConfig, override: SidecarConfig) -> SidecarConfig:
    """Overlay *override* onto *base* (used for template + user sidecar merging).

    - document: field-level merge (non-null wins)
    - defaults: per-block-type merge
    - selectors: concatenated (base first, then override)
    - blocks: per-anchor merge
    """
    document = merge_document_config(base.document, override.document)

    defaults = dict(base.defaults)
    for block_type, style in override.defaults.items():
        if block_type in defaults:
            defaults[block_type] = merge_block_style(defaults[block_type], style)
        else:
            defaults[block_type] = style

    selectors = list(base.selectors) + list(override.selectors)

    blocks = dict(base.blocks)
    for anchor, style in override.blocks.items():
        if anchor in blocks:
            blocks[anchor] = merge_block_style(blocks[anchor], style)
        else:
            blocks[anchor] = style

    return SidecarConfig(
        template=override.template or base.template,
        document=document,
        defaults=defaults,
        selectors=selectors,
        blocks=blocks,
    )
