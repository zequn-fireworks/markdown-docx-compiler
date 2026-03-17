"""Built-in theme defaults and template discovery for the compiler."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

from markdown_docx_compiler._util import as_dict, as_float, as_str
from markdown_docx_compiler.sidecar import (
    BlockStyle,
    DocumentConfig,
    FooterConfig,
    MarginConfig,
    SidecarConfig,
    _block_style_from_dict,
    _parse_sidecar_payload,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Theme:
    name: str
    document: DocumentConfig
    variants: dict[str, dict[str, BlockStyle]] = field(default_factory=dict)


DEFAULT_THEME = Theme(
    name="default",
    document=DocumentConfig(
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
            "body": BlockStyle(),
            "lead": BlockStyle(font_size=12.0, space_after=8.0, line_spacing=1.3),
        },
        "table": {
            "standard": BlockStyle(background_color="F9FAFB"),
            "benchmark": BlockStyle(background_color="EEF2FF", border_color="94A3B8", width="full"),
        },
        "code": {
            "standard": BlockStyle(),
        },
        "blockquote": {
            "standard": BlockStyle(border_color="94A3B8"),
        },
    },
)

_DEFAULT_LAYOUT = SidecarConfig(
    defaults={
        "paragraph": BlockStyle(variant="body", line_spacing=1.25, space_after=6.0),
        "table": BlockStyle(variant="standard", width="full"),
        "code": BlockStyle(
            variant="standard",
            background_color="F3F4F6",
            font_size=9.5,
            line_spacing=1.15,
            space_before=6.0,
            space_after=6.0,
        ),
        "blockquote": BlockStyle(variant="standard", color="4B5563", space_before=8.0, space_after=8.0),
        "list": BlockStyle(variant="standard", space_before=2.0, space_after=2.0),
        "image": BlockStyle(variant="standard", space_before=8.0, space_after=8.0),
    },
)


# ---------------------------------------------------------------------------
# Brand / template loading
# ---------------------------------------------------------------------------


def load_brand_yaml(text: str) -> Theme:
    """Parse a brand YAML string into a Theme.

    Brand YAML defines company-level visual identity: logo placeholder, fonts,
    colors, and variant definitions.  It does *not* include layout defaults or
    selectors — those belong in template layout files.
    """
    payload: Any = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise ValueError("Brand YAML must be a mapping")

    name = as_str(payload.get("name")) or "unknown"

    document = DocumentConfig(
        theme=name,
        logo_path=as_str(payload.get("logo")),
        font=as_str(payload.get("font")),
        mono_font=as_str(payload.get("mono_font")),
        primary_color=as_str(payload.get("primary_color")),
        text_color=as_str(payload.get("text_color")),
        muted_color=as_str(payload.get("muted_color")),
        border_color=as_str(payload.get("border_color")),
        page_width_inches=as_float(payload.get("page_width_inches")),
    )

    variants: dict[str, dict[str, BlockStyle]] = {}
    for block_type, variant_dict in as_dict(payload.get("variants")).items():
        if isinstance(variant_dict, dict):
            variants[block_type] = {
                variant_name: _block_style_from_dict(as_dict(style_data))
                for variant_name, style_data in variant_dict.items()
            }

    return Theme(name=name, document=document, variants=variants)


# ---------------------------------------------------------------------------
# Template discovery via entry points
# ---------------------------------------------------------------------------

_template_cache: dict[str, tuple[Theme, SidecarConfig]] | None = None


def _discover_templates() -> dict[str, tuple[Theme, SidecarConfig]]:
    """Scan ``mdc.templates`` entry points and load all templates.

    Each entry point resolves to a ``Traversable`` package directory containing:
    - ``brand.yaml`` — shared company brand (parsed into a Theme)
    - Other ``.yaml`` files — template layouts (parsed into SidecarConfigs)

    Template naming: ``default.yaml`` registers as ``{company}``,
    others register as ``{company}-{stem}``.
    """
    global _template_cache
    if _template_cache is not None:
        return _template_cache

    from importlib.metadata import entry_points

    templates: dict[str, tuple[Theme, SidecarConfig]] = {}

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
                layout = _parse_sidecar_payload(layout_payload)

                stem = item.name.rsplit(".", 1)[0]
                template_name = company if stem == "default" else f"{company}-{stem}"
                templates[template_name] = (theme, layout)
        except Exception:
            logger.warning("Failed to load templates from entry point %s", ep.name, exc_info=True)

    _template_cache = templates
    return templates


def get_template(name: str) -> tuple[Theme, SidecarConfig] | None:
    """Look up an installed or built-in template by name.

    The ``"default"`` template is always available as a built-in fallback.
    Returns ``(theme, base_sidecar)`` or ``None`` if the template is not found.
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
document-type layout (margins, footer, defaults, selectors) into installable
packages.  Use a template so you only write per-document overrides.

## Install

  uv add markdown-docx-compiler[fireworks]    # one company
  uv add markdown-docx-compiler[templates]    # all companies

## Usage

Set the template in your sidecar:

  template: fireworks-rca

  document:
    footer:
      center: "2026-03-16"
      right: "Draft"

  blocks:
    results-table:
      columns: [3fr, 1fr, 1fr]

Or in front matter:

  ---
  template: fireworks-rca
  ---

Or via CLI:

  mdc document create report.md --template fireworks-rca

## Resolution order

When a template is active, styles cascade as:

  1. Brand (from template)  - fonts, colors, variant definitions
  2. Template layout         - margins, footer, defaults, selectors
  3. User sidecar            - per-document overrides
  4. Front matter            - inline overrides
  5. CLI flags               - command-line overrides

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
        lines.append("Install with:  uv add markdown-docx-compiler[templates]")
        lines.append("")
    return "\n".join(lines)
