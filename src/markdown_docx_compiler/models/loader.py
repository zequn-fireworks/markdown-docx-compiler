"""YAML sidecar loading — parse a ``.docx.yaml`` file into config models.

This module converts raw YAML dicts into the typed config dataclasses
defined in ``config.py`` and ``style.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from markdown_docx_compiler._util import as_bool, as_dict, as_float, as_list_of_str, as_str
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

# ---------------------------------------------------------------------------
# Leaf property-group parsers
# ---------------------------------------------------------------------------


def _font_from_dict(data: dict[str, Any] | None) -> FontStyle | None:
    if not data:
        return None
    return FontStyle(
        family=as_str(data.get("family")),
        size=as_float(data.get("size")),
        color=as_str(data.get("color")),
        bold=as_bool(data.get("bold")),
        italic=as_bool(data.get("italic")),
        underline=as_bool(data.get("underline")),
        strikethrough=as_bool(data.get("strikethrough")),
        small_caps=as_bool(data.get("small_caps")),
        all_caps=as_bool(data.get("all_caps")),
        letter_spacing=as_float(data.get("letter_spacing")),
        highlight=as_str(data.get("highlight")),
    )


def _spacing_from_dict(data: dict[str, Any] | None) -> SpacingStyle | None:
    if not data:
        return None
    return SpacingStyle(
        before=as_float(data.get("before")),
        after=as_float(data.get("after")),
        line=as_float(data.get("line")),
        indent_left=as_float(data.get("indent_left")),
        indent_right=as_float(data.get("indent_right")),
        indent_first_line=as_float(data.get("indent_first_line")),
    )


def _border_side_from_dict(data: dict[str, Any] | None) -> BorderSide | None:
    if not data:
        return None
    return BorderSide(
        color=as_str(data.get("color")),
        width=as_float(data.get("width")),
        style=as_str(data.get("style")),
    )


def _border_from_dict(data: dict[str, Any] | None) -> BorderStyle | None:
    if not data:
        return None
    return BorderStyle(
        top=_border_side_from_dict(as_dict(data.get("top")) or None),
        bottom=_border_side_from_dict(as_dict(data.get("bottom")) or None),
        left=_border_side_from_dict(as_dict(data.get("left")) or None),
        right=_border_side_from_dict(as_dict(data.get("right")) or None),
    )


def _link_from_dict(data: dict[str, Any] | None) -> LinkStyle | None:
    if not data:
        return None
    return LinkStyle(
        color=as_str(data.get("color")),
        underline=as_bool(data.get("underline")),
    )


def _padding_from_dict(data: dict[str, Any] | None) -> PaddingStyle | None:
    if not data:
        return None
    return PaddingStyle(
        top=as_float(data.get("top")),
        bottom=as_float(data.get("bottom")),
        left=as_float(data.get("left")),
        right=as_float(data.get("right")),
    )


def _image_from_dict(data: dict[str, Any] | None) -> ImageProps | None:
    if not data:
        return None
    return ImageProps(
        width=as_str(data.get("width")),
        alignment=as_str(data.get("alignment")),
    )


def _table_from_dict(data: dict[str, Any] | None) -> TableProps | None:
    if not data:
        return None
    return TableProps(
        columns=as_list_of_str(data.get("columns")),
        header_row=as_bool(data.get("header_row")),
        alternating_color=as_str(data.get("alternating_color")),
        cell_padding=_padding_from_dict(as_dict(data.get("cell_padding")) or None),
        border_color=as_str(data.get("border_color")),
    )


# ---------------------------------------------------------------------------
# Composite parsers
# ---------------------------------------------------------------------------


def _block_style_from_dict(data: dict[str, Any] | None) -> BlockStyle:
    data = data or {}
    return BlockStyle(
        font=_font_from_dict(as_dict(data.get("font")) or None),
        spacing=_spacing_from_dict(as_dict(data.get("spacing")) or None),
        background=as_str(data.get("background")),
        border=_border_from_dict(as_dict(data.get("border")) or None),
        alignment=as_str(data.get("alignment")),
        page_break_before=as_bool(data.get("page_break_before")),
        keep_with_next=as_bool(data.get("keep_with_next")),
        width=as_str(data.get("width")),
        link=_link_from_dict(as_dict(data.get("link")) or None),
        image=_image_from_dict(as_dict(data.get("image")) or None),
        table=_table_from_dict(as_dict(data.get("table")) or None),
    )


def _block_override_from_dict(data: dict[str, Any] | None) -> BlockOverride:
    data = data or {}
    block_type = as_str(data.get("type"))
    style = _block_style_from_dict(data)
    return BlockOverride(type=block_type, style=style)


def _margin_from_dict(data: dict[str, Any] | None) -> MarginConfig:
    if not data:
        return MarginConfig()
    return MarginConfig(
        top=as_float(data.get("top")),
        bottom=as_float(data.get("bottom")),
        left=as_float(data.get("left")),
        right=as_float(data.get("right")),
    )


def _page_from_dict(data: dict[str, Any] | None) -> PageConfig:
    if not data:
        return PageConfig()
    return PageConfig(
        width_inches=as_float(data.get("width_inches")),
        margin=_margin_from_dict(as_dict(data.get("margin")) or None),
    )


def _document_config_from_dict(data: dict[str, Any] | None) -> DocumentConfig:
    data = data or {}
    return DocumentConfig(
        title=as_str(data.get("title")),
        font=_font_from_dict(as_dict(data.get("font")) or None) or FontStyle(),
        mono_font=as_str(data.get("mono_font")),
        link=_link_from_dict(as_dict(data.get("link")) or None) or LinkStyle(),
        page=_page_from_dict(as_dict(data.get("page")) or None),
    )


def _region_style_from_dict(data: dict[str, Any] | None) -> RegionStyle:
    if not data:
        return RegionStyle()
    return RegionStyle(
        font=_font_from_dict(as_dict(data.get("font")) or None),
        border=_border_from_dict(as_dict(data.get("border")) or None),
        image=_image_from_dict(as_dict(data.get("image")) or None),
    )


# ---------------------------------------------------------------------------
# Top-level sidecar parsing
# ---------------------------------------------------------------------------


def _parse_sidecar_payload(payload: dict[str, Any]) -> SidecarConfig:
    """Convert a raw YAML dict into a ``SidecarConfig``."""
    defaults: dict[str, BlockStyle] = {}
    for key, value in as_dict(payload.get("defaults")).items():
        defaults[key] = _block_style_from_dict(as_dict(value))

    blocks: dict[str, BlockOverride] = {}
    for key, value in as_dict(payload.get("blocks")).items():
        blocks[key] = _block_override_from_dict(as_dict(value))

    return SidecarConfig(
        extend=as_str(payload.get("extend")),
        document=_document_config_from_dict(as_dict(payload.get("document")) or None),
        page_header=_region_style_from_dict(as_dict(payload.get("page_header")) or None),
        page_footer=_region_style_from_dict(as_dict(payload.get("page_footer")) or None),
        doc_header=_region_style_from_dict(as_dict(payload.get("doc_header")) or None),
        defaults=defaults,
        blocks=blocks,
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Sidecar config must be a mapping: {path}")
    return payload


def load_sidecar(path: Path | None, *, base_dir: Path | None = None) -> SidecarConfig:
    """Load and return a ``SidecarConfig``, resolving ``extend`` if present.

    Parameters
    ----------
    path:
        Path to the sidecar YAML file, or ``None`` for defaults.
    base_dir:
        Directory used to resolve relative ``extend`` paths.  Defaults to
        the parent of *path*.
    """
    if path is None or not path.exists():
        return SidecarConfig()

    payload = _read_yaml(path)
    config = _parse_sidecar_payload(payload)

    if config.extend:
        resolve_dir = base_dir or path.parent
        base_path = (resolve_dir / config.extend).resolve()
        if base_path.exists():
            base_config = load_sidecar(base_path, base_dir=base_path.parent)
            from markdown_docx_compiler.resolve.merge import merge_sidecar_config

            config = merge_sidecar_config(base_config, config)

    return config
