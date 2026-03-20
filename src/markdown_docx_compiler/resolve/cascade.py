"""3-tier style cascade for body blocks.

Resolution order
----------------
1. Built-in defaults (``defaults.py``)
2. Sidecar ``document`` globals + ``defaults[block_type]``
3. Sidecar ``blocks[anchor_id]`` instance overrides

Region styles are resolved separately (they inherit from ``document``
globals but do not participate in the body cascade).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from markdown_docx_compiler._util import as_float, as_str
from markdown_docx_compiler.models.config import (
    DocumentConfig,
    MarginConfig,
    PageConfig,
    RegionStyle,
    SidecarConfig,
)
from markdown_docx_compiler.models.document import BlockNode, block_type_name
from markdown_docx_compiler.models.style import (
    BlockStyle,
    FontStyle,
    LinkStyle,
)
from markdown_docx_compiler.resolve.defaults import (
    DEFAULT_BLOCK_STYLES,
    DEFAULT_DOC_HEADER,
    DEFAULT_DOCUMENT,
    DEFAULT_PAGE_FOOTER,
    DEFAULT_PAGE_HEADER,
)
from markdown_docx_compiler.resolve.merge import (
    merge_block_style,
    merge_document_config,
    merge_region_style,
)

# ---------------------------------------------------------------------------
# Document-level resolution
# ---------------------------------------------------------------------------


def resolve_document_config(
    *,
    sidecar: SidecarConfig,
    front_matter: dict[str, Any] | None = None,
    base_dir: Path | None = None,
) -> tuple[DocumentConfig, SidecarConfig]:
    """Produce the final ``DocumentConfig`` and effective ``SidecarConfig``.

    Cascade: built-in defaults -> sidecar document -> front matter.
    """
    config = merge_document_config(DEFAULT_DOCUMENT, sidecar.document)

    if front_matter:
        fm_config = _document_from_front_matter(front_matter)
        config = merge_document_config(config, fm_config)

    if config.title and base_dir:
        pass  # reserved for future path resolution

    return config, sidecar


def resolve_region_styles(
    sidecar: SidecarConfig,
) -> tuple[RegionStyle, RegionStyle, RegionStyle]:
    """Resolve page_header, page_footer, doc_header styles.

    Each inherits from its built-in default, then overlays the sidecar section.
    """
    page_header = merge_region_style(DEFAULT_PAGE_HEADER, sidecar.page_header)
    page_footer = merge_region_style(DEFAULT_PAGE_FOOTER, sidecar.page_footer)
    doc_header = merge_region_style(DEFAULT_DOC_HEADER, sidecar.doc_header)
    return page_header, page_footer, doc_header


# ---------------------------------------------------------------------------
# Block-level resolution
# ---------------------------------------------------------------------------


def resolve_block_style(
    *,
    block: BlockNode,
    sidecar: SidecarConfig,
    document: DocumentConfig,
) -> BlockStyle:
    """Compute the final style for a single body block.

    Tier 1 — built-in type default, merged with sidecar type default.
    Tier 2 — instance override from ``blocks[anchor]`` (if present).
    Document-level font/link are woven in as the deepest base.
    """
    bt = block_type_name(block)

    doc_base = BlockStyle(
        font=document.font,
        link=document.link,
    )

    builtin_default = DEFAULT_BLOCK_STYLES.get(bt, BlockStyle())
    style = merge_block_style(doc_base, builtin_default)

    sidecar_default = sidecar.defaults.get(bt)
    if sidecar_default is not None:
        style = merge_block_style(style, sidecar_default)

    anchor = block.meta.anchor
    if anchor and anchor in sidecar.blocks:
        override = sidecar.blocks[anchor]
        style = merge_block_style(style, override.style)

    return style


def resolve_all_block_styles(
    *,
    blocks: list[BlockNode],
    sidecar: SidecarConfig,
    document: DocumentConfig,
) -> dict[int, BlockStyle]:
    """Resolve styles for every block in the body, keyed by block index."""
    return {
        block.meta.index: resolve_block_style(
            block=block,
            sidecar=sidecar,
            document=document,
        )
        for block in blocks
    }


# ---------------------------------------------------------------------------
# Front-matter -> DocumentConfig
# ---------------------------------------------------------------------------


def _document_from_front_matter(data: dict[str, Any]) -> DocumentConfig:
    """Extract document-level overrides from YAML front matter."""
    return DocumentConfig(
        title=as_str(data.get("title")),
        font=FontStyle(
            family=as_str(data.get("font")),
            color=as_str(data.get("text_color")),
        ),
        mono_font=as_str(data.get("mono_font")),
        link=LinkStyle(color=as_str(data.get("link_color"))),
        page=PageConfig(
            width_inches=as_float(data.get("page_width_inches")),
            margin=MarginConfig(
                top=as_float(data.get("margin_top")),
                bottom=as_float(data.get("margin_bottom")),
                left=as_float(data.get("margin_left")),
                right=as_float(data.get("margin_right")),
            ),
        ),
    )
