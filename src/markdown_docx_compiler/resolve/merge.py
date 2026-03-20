"""Deep-merge helpers for style and config dataclasses.

Every merge follows the same rule: non-``None`` values in *override*
replace the corresponding values in *base*.  This is applied recursively
for nested dataclass groups (e.g. ``FontStyle`` inside ``BlockStyle``).
"""

from __future__ import annotations

from dataclasses import fields
from typing import TypeVar

from markdown_docx_compiler.models.config import (
    BlockOverride,
    DocumentConfig,
    MarginConfig,
    PageConfig,
    RegionStyle,
    SidecarConfig,
)
from markdown_docx_compiler.models.style import (
    BlockStyle,
    BorderSide,
    BorderStyle,
    FontStyle,
    ImageProps,
    LinkStyle,
    PaddingStyle,
    SpacingStyle,
    TableProps,
)

T = TypeVar("T")

# Types that should be merged field-by-field rather than replaced wholesale.
_MERGEABLE = frozenset(
    {
        FontStyle,
        SpacingStyle,
        BorderSide,
        BorderStyle,
        LinkStyle,
        PaddingStyle,
        ImageProps,
        TableProps,
        BlockStyle,
        MarginConfig,
        PageConfig,
        DocumentConfig,
        RegionStyle,
    }
)


def _merge_dataclass(base: T, override: T) -> T:
    """Merge two frozen dataclasses of the same type, field by field."""
    cls = type(base)
    values: dict[str, object] = {}
    for f in fields(cls):  # type: ignore[arg-type]
        base_val = getattr(base, f.name)
        over_val = getattr(override, f.name)
        if over_val is None:
            values[f.name] = base_val
        elif base_val is None:
            values[f.name] = over_val
        elif type(over_val) in _MERGEABLE and type(base_val) in _MERGEABLE:
            values[f.name] = _merge_dataclass(base_val, over_val)
        else:
            values[f.name] = over_val
    return cls(**values)


# ---------------------------------------------------------------------------
# Public merge functions
# ---------------------------------------------------------------------------


def merge_font(base: FontStyle, override: FontStyle) -> FontStyle:
    return _merge_dataclass(base, override)


def merge_spacing(base: SpacingStyle, override: SpacingStyle) -> SpacingStyle:
    return _merge_dataclass(base, override)


def merge_border_side(base: BorderSide, override: BorderSide) -> BorderSide:
    return _merge_dataclass(base, override)


def merge_border(base: BorderStyle, override: BorderStyle) -> BorderStyle:
    return _merge_dataclass(base, override)


def merge_block_style(base: BlockStyle, override: BlockStyle) -> BlockStyle:
    return _merge_dataclass(base, override)


def merge_document_config(base: DocumentConfig, override: DocumentConfig) -> DocumentConfig:
    return _merge_dataclass(base, override)


def merge_region_style(base: RegionStyle, override: RegionStyle) -> RegionStyle:
    return _merge_dataclass(base, override)


def merge_sidecar_config(base: SidecarConfig, override: SidecarConfig) -> SidecarConfig:
    """Merge two sidecar configs (used for ``inherits`` layering).

    - ``document``, region styles: deep field merge
    - ``defaults``: per-block-type merge
    - ``blocks``: per-anchor merge
    """
    document = merge_document_config(base.document, override.document)
    page_header = merge_region_style(base.page_header, override.page_header)
    page_footer = merge_region_style(base.page_footer, override.page_footer)
    doc_header = merge_region_style(base.doc_header, override.doc_header)

    defaults = dict(base.defaults)
    for block_type, style in override.defaults.items():
        if block_type in defaults:
            defaults[block_type] = merge_block_style(defaults[block_type], style)
        else:
            defaults[block_type] = style

    blocks = dict(base.blocks)
    for anchor, ovr in override.blocks.items():
        if anchor in blocks:
            merged_style = merge_block_style(blocks[anchor].style, ovr.style)
            blocks[anchor] = BlockOverride(type=ovr.type or blocks[anchor].type, style=merged_style)
        else:
            blocks[anchor] = ovr

    return SidecarConfig(
        inherits=override.inherits or base.inherits,
        document=document,
        page_header=page_header,
        page_footer=page_footer,
        doc_header=doc_header,
        defaults=defaults,
        blocks=blocks,
    )
