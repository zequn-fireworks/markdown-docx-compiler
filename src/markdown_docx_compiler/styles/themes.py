"""Built-in theme defaults and template discovery for the compiler.

This module is self-contained: it defines its own ``Theme``, brand
``DocumentConfig``, and variant ``BlockStyle`` types that are separate
from the document pipeline models.  Template layouts are parsed into
the pipeline's ``SidecarConfig`` via ``models.loader``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

from markdown_docx_compiler._util import (
    as_bool,
    as_dict,
    as_float,
    as_list_of_str,
    as_str,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brand-level types (used only by the theme/template system)
# ---------------------------------------------------------------------------


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
class BrandDocumentConfig:
    """Brand-level document identity for templates (fonts, colors, margins)."""

    theme: str | None = None
    title: str | None = None
    logo_path: str | None = None
    logo_width_inches: float | None = None
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
class BrandBlockStyle:
    """Variant block style for templates (subset of styling properties)."""

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


def _brand_block_style_from_dict(data: dict[str, Any] | None) -> BrandBlockStyle:
    data = data or {}
    return BrandBlockStyle(
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


# Sidecar types used only for template layouts
# (kept here to avoid dependency on deleted old pipeline modules)


@dataclass(frozen=True)
class _TemplateSidecarConfig:
    """Minimal sidecar representation for template layouts."""

    template: str | None = None
    document: BrandDocumentConfig = field(default_factory=BrandDocumentConfig)
    defaults: dict[str, BrandBlockStyle] = field(default_factory=dict)
    blocks: dict[str, BrandBlockStyle] = field(default_factory=dict)


@dataclass(frozen=True)
class Theme:
    name: str
    document: BrandDocumentConfig
    variants: dict[str, dict[str, BrandBlockStyle]] = field(default_factory=dict)


DEFAULT_THEME = Theme(
    name="default",
    document=BrandDocumentConfig(
        theme="default",
        font="Aptos",
        mono_font="Consolas",
        primary_color="1F2937",
        text_color="111827",
        muted_color="6B7280",
        border_color="D1D5DB",
        page_width_inches=8.5,
        margin=MarginConfig(top_inches=1.0, bottom_inches=0.8, left_inches=1.0, right_inches=1.0),
        footer=FooterConfig(left="", center="", right="", show_page_numbers=True),
    ),
    variants={
        "paragraph": {
            "body": BrandBlockStyle(),
            "lead": BrandBlockStyle(font_size=12.0, space_after=8.0, line_spacing=1.3),
        },
        "table": {
            "standard": BrandBlockStyle(background_color="F9FAFB"),
            "benchmark": BrandBlockStyle(background_color="EEF2FF", border_color="94A3B8", width="full"),
        },
        "code": {
            "standard": BrandBlockStyle(),
        },
        "blockquote": {
            "standard": BrandBlockStyle(border_color="94A3B8"),
        },
    },
)

_DEFAULT_LAYOUT = _TemplateSidecarConfig(
    defaults={
        "paragraph": BrandBlockStyle(variant="body", line_spacing=1.25, space_after=6.0),
        "table": BrandBlockStyle(variant="standard", width="full"),
        "code": BrandBlockStyle(
            variant="standard",
            background_color="F3F4F6",
            font_size=9.5,
            line_spacing=1.15,
            space_before=6.0,
            space_after=6.0,
        ),
        "blockquote": BrandBlockStyle(variant="standard", color="4B5563", space_before=8.0, space_after=8.0),
        "list": BrandBlockStyle(variant="standard", space_before=2.0, space_after=2.0),
        "image": BrandBlockStyle(variant="standard", space_before=8.0, space_after=8.0),
    },
)


# ---------------------------------------------------------------------------
# Brand / template loading
# ---------------------------------------------------------------------------


def load_brand_yaml(text: str) -> Theme:
    """Parse a brand YAML string into a Theme.

    Brand YAML defines company-level visual identity: logo placeholder, fonts,
    colors, and variant definitions.  It does *not* include layout defaults —
    those belong in template layout files.
    """
    payload: Any = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise ValueError("Brand YAML must be a mapping")

    name = as_str(payload.get("name")) or "unknown"

    document = BrandDocumentConfig(
        theme=name,
        logo_path=as_str(payload.get("logo")),
        logo_width_inches=as_float(payload.get("logo_width_inches")),
        font=as_str(payload.get("font")),
        mono_font=as_str(payload.get("mono_font")),
        primary_color=as_str(payload.get("primary_color")),
        text_color=as_str(payload.get("text_color")),
        muted_color=as_str(payload.get("muted_color")),
        border_color=as_str(payload.get("border_color")),
        page_width_inches=as_float(payload.get("page_width_inches")),
    )

    variants: dict[str, dict[str, BrandBlockStyle]] = {}
    for block_type, variant_dict in as_dict(payload.get("variants")).items():
        if isinstance(variant_dict, dict):
            variants[block_type] = {
                variant_name: _brand_block_style_from_dict(as_dict(style_data))
                for variant_name, style_data in variant_dict.items()
            }

    return Theme(name=name, document=document, variants=variants)


# ---------------------------------------------------------------------------
# Template discovery via entry points
# ---------------------------------------------------------------------------


def _parse_template_layout(payload: dict[str, Any]) -> _TemplateSidecarConfig:
    """Parse a template layout YAML dict into a ``_TemplateSidecarConfig``."""
    doc_data = payload.get("document") or {}
    doc = BrandDocumentConfig(
        theme=as_str(doc_data.get("theme")),
        title=as_str(doc_data.get("title")),
        font=as_str(doc_data.get("font")),
        mono_font=as_str(doc_data.get("mono_font")),
        primary_color=as_str(doc_data.get("primary_color")),
        text_color=as_str(doc_data.get("text_color")),
        muted_color=as_str(doc_data.get("muted_color")),
        border_color=as_str(doc_data.get("border_color")),
    )
    defaults: dict[str, BrandBlockStyle] = {}
    for key, value in (payload.get("defaults") or {}).items():
        if isinstance(value, dict):
            defaults[key] = _brand_block_style_from_dict(value)
    blocks: dict[str, BrandBlockStyle] = {}
    for key, value in (payload.get("blocks") or {}).items():
        if isinstance(value, dict):
            blocks[key] = _brand_block_style_from_dict(value)
    return _TemplateSidecarConfig(
        template=as_str(payload.get("template")),
        document=doc,
        defaults=defaults,
        blocks=blocks,
    )


_template_cache: dict[str, tuple[Theme, _TemplateSidecarConfig]] | None = None


def _discover_templates() -> dict[str, tuple[Theme, _TemplateSidecarConfig]]:
    """Scan ``mdc.templates`` entry points and load all templates.

    Each entry point resolves to a ``Traversable`` package directory containing:
    - ``brand.yaml`` — shared company brand (parsed into a Theme)
    - Other ``.yaml`` files — template layouts (parsed into _TemplateSidecarConfigs)

    Template naming: ``default.yaml`` registers as ``{company}``,
    others register as ``{company}-{stem}``.
    """
    global _template_cache
    if _template_cache is not None:
        return _template_cache

    from importlib.metadata import entry_points

    templates: dict[str, tuple[Theme, _TemplateSidecarConfig]] = {}

    for ep in entry_points(group="mdc.templates"):
        try:
            template_dir = ep.load()
            company = ep.name

            brand_text = (template_dir / "brand.yaml").read_text(encoding="utf-8")
            theme = load_brand_yaml(brand_text)

            for item in template_dir.iterdir():
                if not item.name.endswith((".yaml", ".yml")):
                    continue
                if item.name.startswith("brand"):
                    continue
                layout_text = item.read_text(encoding="utf-8")
                layout_payload: Any = yaml.safe_load(layout_text) or {}
                if not isinstance(layout_payload, dict):
                    continue
                layout = _parse_template_layout(layout_payload)

                stem = item.name.rsplit(".", 1)[0]
                template_name = company if stem == "default" else f"{company}-{stem}"
                templates[template_name] = (theme, layout)
        except (OSError, ValueError, KeyError, yaml.YAMLError):
            logger.warning("Failed to load templates from entry point %s", ep.name, exc_info=True)

    _template_cache = templates
    return templates


def get_template(name: str) -> tuple[Theme, _TemplateSidecarConfig] | None:
    """Look up an installed or built-in template by name.

    The ``"default"`` template is always available as a built-in fallback.
    Returns ``(theme, layout)`` or ``None`` if the template is not found.
    """
    if name == "default":
        return DEFAULT_THEME, _DEFAULT_LAYOUT
    return _discover_templates().get(name)


def _reset_template_cache() -> None:
    """Clear the template cache (for testing)."""
    global _template_cache
    _template_cache = None


def help_topic() -> str:
    """Generate the themes/templates help topic.

    Lists the built-in default brand, installed templates, and their
    variant definitions.
    """
    lines = [
        "# Themes & Templates",
        "",
        "Templates provide brand identity (fonts, colors, variants) and",
        "document layout (margins, footer, defaults).  Set `template:` in",
        "your sidecar, front matter, or via `--template` on the CLI.",
        "",
        "## Built-in default brand",
        "",
    ]
    doc = DEFAULT_THEME.document
    lines.append(f"  font:          {doc.font}")
    lines.append(f"  mono_font:     {doc.mono_font}")
    lines.append(f"  primary_color: #{doc.primary_color}")
    lines.append(f"  text_color:    #{doc.text_color}")
    lines.append(f"  muted_color:   #{doc.muted_color}")
    lines.append(f"  border_color:  #{doc.border_color}")
    lines.append("")
    if DEFAULT_THEME.variants:
        lines.append("  Variants:")
        for block_type, variants in DEFAULT_THEME.variants.items():
            variant_names = ", ".join(variants.keys())
            lines.append(f"    {block_type}: {variant_names}")
        lines.append("")

    templates = _discover_templates()
    if templates:
        lines.append("## Installed templates")
        lines.append("")
        lines.append("Use `mdc template list` for details, or set `template:` in your sidecar.")
        lines.append("")
        for template_name in sorted(templates):
            lines.append(f"  - {template_name}")
        lines.append("")

    return "\n".join(lines)


TEMPLATES_HELP_TOPIC = """\
# Templates

Templates bundle a company's brand identity (fonts, colors, variants) with
document-type layout (margins, footer, defaults) into installable
packages.  Use a template so you only write per-document overrides.

## Install

Install a template package into the same environment as
`markdown-docx-compiler`:

  pip install mdc-acme-templates

## Usage

Set the template in your sidecar:

  template: acme-report

  document:
    footer:
      center: "2026-03-16"
      right: "Draft"

  blocks:
    results-table:
      columns: [3fr, 1fr, 1fr]

Or in front matter:

  ---
  template: acme-report
  ---

Then inspect or compile as usual:

  mdc template list
  mdc template show acme-report
  mdc doc create report.md -o report.docx

## Resolution order

When a template is active, styles cascade as:

  1. Built-in defaults       - base fonts, colors, margins
  2. Sidecar config          - document settings, defaults, block overrides
  3. Front matter            - inline document-level overrides

## Providing a logo

Templates ship without logo images.  Provide your own via sidecar:

  document:
    logo_path: ./assets/our-logo.png

## Available templates
"""


def templates_help_topic() -> str:
    """Generate the templates help topic with a listing of installed templates."""
    lines = [TEMPLATES_HELP_TOPIC.rstrip()]
    templates = _discover_templates()
    if templates:
        lines.append("")
        for template_name, (theme, _layout) in sorted(templates.items()):
            doc = theme.document
            desc = f"brand={theme.name}, font={doc.font}"
            lines.append(f"  {template_name:30s} {desc}")
        lines.append("")
    else:
        lines.append("")
        lines.append("  (none installed)")
        lines.append("")
        lines.append("Install a package exposing the `mdc.templates` entry point, for example:")
        lines.append("  pip install mdc-acme-templates")
        lines.append("")
    return "\n".join(lines)
