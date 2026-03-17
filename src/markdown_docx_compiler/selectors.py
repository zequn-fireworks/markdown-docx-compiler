"""Style resolution helpers for blocks and documents."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from markdown_docx_compiler._util import as_float, as_str
from markdown_docx_compiler.ir import (
    BlockNode,
    BlockQuoteBlock,
    CodeBlock,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)
from markdown_docx_compiler.sidecar import (
    BlockStyle,
    DocumentConfig,
    SelectorMatch,
    SidecarConfig,
    merge_block_style,
    merge_document_config,
    merge_sidecar_config,
)
from markdown_docx_compiler.styles import Theme, get_template
from markdown_docx_compiler.styles.themes import _DEFAULT_LAYOUT, DEFAULT_THEME

HELP_TOPIC = """\
# Selectors

Selectors match blocks by criteria and apply styles without requiring anchors.
They are evaluated in declaration order; all matching selectors are merged.

## Structure

  selectors:
    - match:
        <criteria>
      apply:
        <block style properties>

## Match fields

  type           str   Block type: paragraph, table, code, blockquote,
                       list, image, heading
  heading        str   Heading text the block falls under, or
                       "__document__" for the first block in the document
  index          int   Block index (1-based position in the document)
  anchor         str   Anchor ID from <!-- docx:id=name -->
  column_count   int   Table column count (tables only)

All match fields are optional.  When multiple fields are set, all must match.

## Examples

Style the first paragraph under a specific heading as a lead:

  selectors:
    - match:
        type: paragraph
        heading: "Benchmark Report"
      apply:
        variant: lead

Style all 3-column tables as benchmark tables:

  selectors:
    - match:
        type: table
        column_count: 3
      apply:
        variant: benchmark
        columns: [3fr, 1fr, 1fr]

Add a page break before the appendix heading:

  selectors:
    - match:
        type: heading
        heading: Appendix
      apply:
        page_break_before: true

See `mdc help sidecar` for the full list of block style properties.
"""


def resolve_document_config(
    *,
    front_matter: dict[str, Any],
    sidecar: SidecarConfig,
    cli_overrides: DocumentConfig | None = None,
    template_override: str | None = None,
    base_dir: Path,
) -> tuple[Theme, DocumentConfig, SidecarConfig]:
    """Resolve the final document-level config.

    Returns the resolved theme, merged document config, and the effective
    sidecar (which includes merged template config when a template is active).
    """
    template_name = template_override or as_str(front_matter.get("template")) or sidecar.template

    template_result = get_template(template_name) if template_name else None

    if template_result is not None:
        theme, base_sidecar = template_result
        sidecar = merge_sidecar_config(base_sidecar, sidecar)
    else:
        theme = DEFAULT_THEME
        sidecar = merge_sidecar_config(_DEFAULT_LAYOUT, sidecar)

    config = theme.document
    config = merge_document_config(config, sidecar.document)
    config = merge_document_config(config, _document_from_front_matter(front_matter))
    if cli_overrides is not None:
        config = merge_document_config(config, cli_overrides)
    if config.logo_path:
        config = replace(config, logo_path=_resolve_optional_path(config.logo_path, base_dir=base_dir))
    return theme, config, sidecar


def resolve_block_style(
    *,
    block: BlockNode,
    sidecar: SidecarConfig,
    theme: Theme,
) -> BlockStyle:
    """Resolve the final block style for a parsed block.

    Block defaults now live in the sidecar (merged from template layout
    during document config resolution), not in the Theme.
    """
    block_type = block_type_name(block)
    style = sidecar.defaults.get(block_type, BlockStyle())

    theme_variant = style.variant
    if theme_variant:
        style = merge_block_style(style, theme.variants.get(block_type, {}).get(theme_variant, BlockStyle()))

    for rule in sidecar.selectors:
        if _rule_matches(block=block, rule=rule.match):
            style = merge_block_style(style, rule.apply)

    if block.meta.anchor and block.meta.anchor in sidecar.blocks:
        style = merge_block_style(style, sidecar.blocks[block.meta.anchor])

    variant = style.variant
    if variant:
        style = merge_block_style(theme.variants.get(block_type, {}).get(variant, BlockStyle()), style)

    return style


def block_type_name(block: BlockNode) -> str:
    if isinstance(block, HeadingBlock):
        return "heading"
    if isinstance(block, ParagraphBlock):
        return "paragraph"
    if isinstance(block, HorizontalRuleBlock):
        return "horizontal_rule"
    if isinstance(block, CodeBlock):
        return "code"
    if isinstance(block, ImageBlock):
        return "image"
    if isinstance(block, BlockQuoteBlock):
        return "blockquote"
    if isinstance(block, TableBlock):
        return "table"
    if isinstance(block, ListBlock):
        return "list"
    return "unknown"


def _rule_matches(*, block: BlockNode, rule: SelectorMatch) -> bool:
    if rule.type and rule.type != block_type_name(block):
        return False
    if rule.anchor and rule.anchor != block.meta.anchor:
        return False
    if rule.index is not None and rule.index != block.meta.index:
        return False
    if rule.heading:
        heading_path = list(block.meta.heading_path)
        if not heading_path:
            return False
        if rule.heading != "__document__" and rule.heading not in heading_path:
            return False
        if rule.heading == "__document__" and block.meta.index != 1:
            return False
    if rule.column_count is not None and (  # noqa: SIM103
        not isinstance(block, TableBlock) or block.column_count != rule.column_count
    ):
        return False
    return True


def _document_from_front_matter(data: dict[str, Any]) -> DocumentConfig:
    footer_raw = data.get("footer")
    footer_data: dict[str, Any] = footer_raw if isinstance(footer_raw, dict) else {}
    from markdown_docx_compiler.sidecar import FooterConfig, MarginConfig

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
        margin=MarginConfig(
            top_inches=as_float(data.get("margin_top_inches")),
            bottom_inches=as_float(data.get("margin_bottom_inches")),
            left_inches=as_float(data.get("margin_left_inches")),
            right_inches=as_float(data.get("margin_right_inches")),
        ),
        footer=FooterConfig(
            left=as_str(data.get("footer_left") or footer_data.get("left")),
            center=as_str(data.get("footer_center") or footer_data.get("center")),
            right=as_str(data.get("footer_right") or footer_data.get("right")),
        ),
    )


def _resolve_optional_path(path: str, *, base_dir: Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str((base_dir / candidate).resolve())
