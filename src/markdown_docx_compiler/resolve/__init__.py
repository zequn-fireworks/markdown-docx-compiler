"""Style resolution and cascade logic."""

from .cascade import (
    resolve_all_block_styles,
    resolve_block_style,
    resolve_document_config,
    resolve_region_styles,
)
from .merge import (
    merge_block_style,
    merge_document_config,
    merge_region_style,
    merge_sidecar_config,
)

__all__ = [
    "merge_block_style",
    "merge_document_config",
    "merge_region_style",
    "merge_sidecar_config",
    "resolve_all_block_styles",
    "resolve_block_style",
    "resolve_document_config",
    "resolve_region_styles",
]
