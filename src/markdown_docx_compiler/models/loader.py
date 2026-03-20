"""YAML sidecar loading — parse a ``.docx.yaml`` file into config models.

This module converts raw YAML dicts into the typed config dataclasses
defined in ``config.py`` and ``style.py``.
"""

from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path
from typing import Any

import yaml

from markdown_docx_compiler._util import as_bool, as_float, as_list_of_str, as_str
from markdown_docx_compiler.models.config import (
    BlockOverride,
    DocumentConfig,
    MarginConfig,
    PageConfig,
    RegionStyle,
    SidecarConfig,
)
from markdown_docx_compiler.models.document import BLOCK_TYPE_NAMES
from markdown_docx_compiler.models.style import (
    BlockStyle,
    BorderSide,
    BorderStyle,
    FontStyle,
    ImageProps,
    LinkStyle,
    ListProps,
    PaddingStyle,
    SpacingStyle,
    TableProps,
)

_FONT_KEYS = frozenset(f.name for f in fields(FontStyle))
_SPACING_KEYS = frozenset(f.name for f in fields(SpacingStyle))
_BORDER_SIDE_KEYS = frozenset(f.name for f in fields(BorderSide))
_BORDER_KEYS = frozenset(f.name for f in fields(BorderStyle))
_LINK_KEYS = frozenset(f.name for f in fields(LinkStyle))
_PADDING_KEYS = frozenset(f.name for f in fields(PaddingStyle))
_IMAGE_KEYS = frozenset(f.name for f in fields(ImageProps))
_LIST_KEYS = frozenset(f.name for f in fields(ListProps))
_TABLE_KEYS = frozenset(f.name for f in fields(TableProps))
_BLOCK_STYLE_KEYS = frozenset(f.name for f in fields(BlockStyle))
_BLOCK_OVERRIDE_KEYS = _BLOCK_STYLE_KEYS | {"type"}
_MARGIN_KEYS = frozenset(f.name for f in fields(MarginConfig))
_PAGE_KEYS = frozenset(f.name for f in fields(PageConfig))
_DOCUMENT_KEYS = frozenset(f.name for f in fields(DocumentConfig))
_REGION_KEYS = frozenset(f.name for f in fields(RegionStyle))

_TOP_LEVEL_KEYS = frozenset(
    {
        "inherits",
        "document",
        "page_header",
        "page_footer",
        "doc_header",
        "defaults",
        "blocks",
    }
)
_BLOCK_TYPE_VALUES = frozenset(BLOCK_TYPE_NAMES.values())
_ALIGNMENT_VALUES = frozenset({"left", "center", "right", "justify"})
_IMAGE_ALIGNMENT_VALUES = frozenset({"left", "center", "right"})
_LIST_NUMBERING_VALUES = frozenset({"decimal_hierarchical", "alpha_hierarchical", "alpha_paren_hierarchical"})
_BORDER_STYLE_VALUES = frozenset({"single", "double", "dotted", "dashed", "none"})
_MEASUREMENT_RE = re.compile(r"^\d+(?:\.\d+)?in$")
_PERCENT_RE = re.compile(r"^\d+(?:\.\d+)?%$")
_FR_RE = re.compile(r"^(?:\d+(?:\.\d+)?)?fr$")


def _validate_keys(data: dict[str, Any], allowed: frozenset[str], *, context: str) -> None:
    unknown_keys = sorted(set(data) - allowed)
    if unknown_keys:
        keys = ", ".join(unknown_keys)
        allowed_keys = ", ".join(sorted(allowed))
        raise ValueError(f"Unknown {context} key(s): {keys}. Allowed keys: {allowed_keys}.")


def _mapping_or_none(data: dict[str, Any], key: str, *, context: str) -> dict[str, Any] | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {context}.{key}: expected a mapping.")
    return value


def _read_str(data: dict[str, Any], key: str, *, context: str) -> str | None:
    if key not in data or data[key] is None:
        return None
    result = as_str(data.get(key))
    if result is None:
        raise ValueError(f"Invalid {context}.{key}: expected a string.")
    return result


def _read_float(data: dict[str, Any], key: str, *, context: str) -> float | None:
    if key not in data or data[key] is None:
        return None
    result = as_float(data.get(key))
    if result is None:
        raise ValueError(f"Invalid {context}.{key}: expected a number.")
    return result


def _read_bool(data: dict[str, Any], key: str, *, context: str) -> bool | None:
    if key not in data or data[key] is None:
        return None
    result = as_bool(data.get(key))
    if result is None:
        raise ValueError(f"Invalid {context}.{key}: expected a boolean.")
    return result


def _read_list_of_str(data: dict[str, Any], key: str, *, context: str) -> list[str] | None:
    if key not in data or data[key] is None:
        return None
    result = as_list_of_str(data.get(key))
    if result is None:
        raise ValueError(f"Invalid {context}.{key}: expected a list.")
    return result


def _validate_choice(value: str | None, allowed: frozenset[str], *, context: str) -> None:
    if value is None:
        return
    if value.lower() not in allowed:
        options = ", ".join(sorted(allowed))
        raise ValueError(f"Invalid {context}: expected one of {options}.")


def _validate_image_width(value: str | None, *, context: str) -> None:
    if value is None:
        return
    normalized = value.lower()
    if normalized == "auto" or _MEASUREMENT_RE.fullmatch(normalized) or _PERCENT_RE.fullmatch(normalized):
        return
    raise ValueError(f"Invalid {context}: expected `auto`, `<number>in`, or `<number>%`.")


def _validate_block_width(value: str | None, *, context: str) -> None:
    if value is None:
        return
    normalized = value.lower()
    if normalized in {"auto", "full"} or _MEASUREMENT_RE.fullmatch(normalized) or _PERCENT_RE.fullmatch(normalized):
        return
    raise ValueError(f"Invalid {context}: expected `auto`, `full`, `<number>in`, or `<number>%`.")


def _validate_table_columns(specs: list[str] | None, *, context: str) -> None:
    if specs is None:
        return
    for spec in specs:
        normalized = spec.lower()
        if _FR_RE.fullmatch(normalized) or _MEASUREMENT_RE.fullmatch(normalized) or _PERCENT_RE.fullmatch(normalized):
            continue
        raise ValueError(f"Invalid {context}: unsupported column width spec `{spec}`.")


# ---------------------------------------------------------------------------
# Leaf property-group parsers
# ---------------------------------------------------------------------------


def _font_from_dict(data: dict[str, Any] | None) -> FontStyle | None:
    if not data:
        return None
    _validate_keys(data, _FONT_KEYS, context="font")
    return FontStyle(
        family=_read_str(data, "family", context="font"),
        size=_read_float(data, "size", context="font"),
        color=_read_str(data, "color", context="font"),
        bold=_read_bool(data, "bold", context="font"),
        italic=_read_bool(data, "italic", context="font"),
        underline=_read_bool(data, "underline", context="font"),
        strikethrough=_read_bool(data, "strikethrough", context="font"),
        small_caps=_read_bool(data, "small_caps", context="font"),
        all_caps=_read_bool(data, "all_caps", context="font"),
        letter_spacing=_read_float(data, "letter_spacing", context="font"),
        highlight=_read_str(data, "highlight", context="font"),
    )


def _spacing_from_dict(data: dict[str, Any] | None) -> SpacingStyle | None:
    if not data:
        return None
    _validate_keys(data, _SPACING_KEYS, context="spacing")
    return SpacingStyle(
        before=_read_float(data, "before", context="spacing"),
        after=_read_float(data, "after", context="spacing"),
        line=_read_float(data, "line", context="spacing"),
        indent_left=_read_float(data, "indent_left", context="spacing"),
        indent_right=_read_float(data, "indent_right", context="spacing"),
        indent_first_line=_read_float(data, "indent_first_line", context="spacing"),
    )


def _border_side_from_dict(data: dict[str, Any] | None) -> BorderSide | None:
    if not data:
        return None
    _validate_keys(data, _BORDER_SIDE_KEYS, context="border side")
    style = _read_str(data, "style", context="border side")
    _validate_choice(style, _BORDER_STYLE_VALUES, context="border side.style")
    return BorderSide(
        color=_read_str(data, "color", context="border side"),
        width=_read_float(data, "width", context="border side"),
        style=style.lower() if style is not None else None,
    )


def _border_from_dict(data: dict[str, Any] | None) -> BorderStyle | None:
    if not data:
        return None
    _validate_keys(data, _BORDER_KEYS, context="border")
    return BorderStyle(
        top=_border_side_from_dict(_mapping_or_none(data, "top", context="border")),
        bottom=_border_side_from_dict(_mapping_or_none(data, "bottom", context="border")),
        left=_border_side_from_dict(_mapping_or_none(data, "left", context="border")),
        right=_border_side_from_dict(_mapping_or_none(data, "right", context="border")),
    )


def _link_from_dict(data: dict[str, Any] | None) -> LinkStyle | None:
    if not data:
        return None
    _validate_keys(data, _LINK_KEYS, context="link")
    return LinkStyle(
        color=_read_str(data, "color", context="link"),
        underline=_read_bool(data, "underline", context="link"),
    )


def _padding_from_dict(data: dict[str, Any] | None) -> PaddingStyle | None:
    if not data:
        return None
    _validate_keys(data, _PADDING_KEYS, context="padding")
    return PaddingStyle(
        top=_read_float(data, "top", context="padding"),
        bottom=_read_float(data, "bottom", context="padding"),
        left=_read_float(data, "left", context="padding"),
        right=_read_float(data, "right", context="padding"),
    )


def _image_from_dict(data: dict[str, Any] | None) -> ImageProps | None:
    if not data:
        return None
    _validate_keys(data, _IMAGE_KEYS, context="image")
    width = _read_str(data, "width", context="image")
    alignment = _read_str(data, "alignment", context="image")
    _validate_image_width(width, context="image.width")
    _validate_choice(alignment, _IMAGE_ALIGNMENT_VALUES, context="image.alignment")
    return ImageProps(
        width=width,
        alignment=alignment.lower() if alignment is not None else None,
    )


def _list_from_dict(data: dict[str, Any] | None) -> ListProps | None:
    if not data:
        return None
    _validate_keys(data, _LIST_KEYS, context="list")
    numbering = _read_str(data, "numbering", context="list")
    _validate_choice(numbering, _LIST_NUMBERING_VALUES, context="list.numbering")
    return ListProps(
        numbering=numbering.lower() if numbering is not None else None,
    )


def _table_from_dict(data: dict[str, Any] | None) -> TableProps | None:
    if not data:
        return None
    _validate_keys(data, _TABLE_KEYS, context="table")
    columns = _read_list_of_str(data, "columns", context="table")
    _validate_table_columns(columns, context="table.columns")
    return TableProps(
        columns=columns,
        header_row=_read_bool(data, "header_row", context="table"),
        alternating_color=_read_str(data, "alternating_color", context="table"),
        cell_padding=_padding_from_dict(_mapping_or_none(data, "cell_padding", context="table")),
        border_color=_read_str(data, "border_color", context="table"),
    )


# ---------------------------------------------------------------------------
# Composite parsers
# ---------------------------------------------------------------------------


def _block_style_from_dict(data: dict[str, Any] | None) -> BlockStyle:
    data = data or {}
    _validate_keys(data, _BLOCK_STYLE_KEYS, context="block style")
    alignment = _read_str(data, "alignment", context="block style")
    _validate_choice(alignment, _ALIGNMENT_VALUES, context="block style.alignment")
    width = _read_str(data, "width", context="block style")
    _validate_block_width(width, context="block style.width")
    return BlockStyle(
        font=_font_from_dict(_mapping_or_none(data, "font", context="block style")),
        spacing=_spacing_from_dict(_mapping_or_none(data, "spacing", context="block style")),
        background=_read_str(data, "background", context="block style"),
        border=_border_from_dict(_mapping_or_none(data, "border", context="block style")),
        alignment=alignment.lower() if alignment is not None else None,
        page_break_before=_read_bool(data, "page_break_before", context="block style"),
        keep_with_next=_read_bool(data, "keep_with_next", context="block style"),
        width=width,
        link=_link_from_dict(_mapping_or_none(data, "link", context="block style")),
        image=_image_from_dict(_mapping_or_none(data, "image", context="block style")),
        list=_list_from_dict(_mapping_or_none(data, "list", context="block style")),
        table=_table_from_dict(_mapping_or_none(data, "table", context="block style")),
    )


def _block_override_from_dict(data: dict[str, Any] | None) -> BlockOverride:
    data = data or {}
    _validate_keys(data, _BLOCK_OVERRIDE_KEYS, context="block override")
    block_type = _read_str(data, "type", context="block override")
    _validate_choice(block_type, _BLOCK_TYPE_VALUES, context="block override.type")
    style = _block_style_from_dict({key: value for key, value in data.items() if key != "type"})
    return BlockOverride(type=block_type.lower() if block_type is not None else None, style=style)


def _margin_from_dict(data: dict[str, Any] | None) -> MarginConfig:
    if not data:
        return MarginConfig()
    _validate_keys(data, _MARGIN_KEYS, context="margin")
    return MarginConfig(
        top=_read_float(data, "top", context="margin"),
        bottom=_read_float(data, "bottom", context="margin"),
        left=_read_float(data, "left", context="margin"),
        right=_read_float(data, "right", context="margin"),
    )


def _page_from_dict(data: dict[str, Any] | None) -> PageConfig:
    if not data:
        return PageConfig()
    _validate_keys(data, _PAGE_KEYS, context="page")
    return PageConfig(
        width_inches=_read_float(data, "width_inches", context="page"),
        margin=_margin_from_dict(_mapping_or_none(data, "margin", context="page")),
    )


def _document_config_from_dict(data: dict[str, Any] | None) -> DocumentConfig:
    data = data or {}
    _validate_keys(data, _DOCUMENT_KEYS, context="document")
    return DocumentConfig(
        title=_read_str(data, "title", context="document"),
        font=_font_from_dict(_mapping_or_none(data, "font", context="document")) or FontStyle(),
        mono_font=_read_str(data, "mono_font", context="document"),
        link=_link_from_dict(_mapping_or_none(data, "link", context="document")) or LinkStyle(),
        page=_page_from_dict(_mapping_or_none(data, "page", context="document")),
    )


def _region_style_from_dict(data: dict[str, Any] | None) -> RegionStyle:
    if not data:
        return RegionStyle()
    _validate_keys(data, _REGION_KEYS, context="region")
    return RegionStyle(
        font=_font_from_dict(_mapping_or_none(data, "font", context="region")),
        border=_border_from_dict(_mapping_or_none(data, "border", context="region")),
        image=_image_from_dict(_mapping_or_none(data, "image", context="region")),
    )


# ---------------------------------------------------------------------------
# Top-level sidecar parsing
# ---------------------------------------------------------------------------


def _parse_sidecar_payload(payload: dict[str, Any]) -> SidecarConfig:
    """Convert a raw YAML dict into a ``SidecarConfig``."""
    unknown_keys = sorted(set(payload) - _TOP_LEVEL_KEYS)
    if unknown_keys:
        keys = ", ".join(unknown_keys)
        allowed = ", ".join(sorted(_TOP_LEVEL_KEYS))
        raise ValueError(f"Unknown sidecar top-level key(s): {keys}. Allowed keys: {allowed}.")

    inherits = _read_str(payload, "inherits", context="sidecar")
    document_data = _mapping_or_none(payload, "document", context="sidecar")
    page_header_data = _mapping_or_none(payload, "page_header", context="sidecar")
    page_footer_data = _mapping_or_none(payload, "page_footer", context="sidecar")
    doc_header_data = _mapping_or_none(payload, "doc_header", context="sidecar")
    defaults_data = _mapping_or_none(payload, "defaults", context="sidecar") or {}
    blocks_data = _mapping_or_none(payload, "blocks", context="sidecar") or {}

    defaults: dict[str, BlockStyle] = {}
    for key, value in defaults_data.items():
        if not isinstance(value, dict):
            raise ValueError(f"Invalid defaults.{key}: expected a mapping.")
        defaults[key] = _block_style_from_dict(value)

    blocks: dict[str, BlockOverride] = {}
    for key, value in blocks_data.items():
        if not isinstance(value, dict):
            raise ValueError(f"Invalid blocks.{key}: expected a mapping.")
        blocks[key] = _block_override_from_dict(value)

    return SidecarConfig(
        inherits=inherits,
        document=_document_config_from_dict(document_data),
        page_header=_region_style_from_dict(page_header_data),
        page_footer=_region_style_from_dict(page_footer_data),
        doc_header=_region_style_from_dict(doc_header_data),
        defaults=defaults,
        blocks=blocks,
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Sidecar config must be a mapping: {path}")
    return payload


def load_sidecar(path: Path | None) -> SidecarConfig:
    """Load and return a ``SidecarConfig``, resolving ``inherits`` if present.

    Parameters
    ----------
    path:
        Path to the sidecar YAML file, or ``None`` for defaults.
    """
    if path is None:
        return SidecarConfig()
    return _load_sidecar(path.resolve(), chain=())


def _load_sidecar(path: Path, *, chain: tuple[Path, ...]) -> SidecarConfig:
    if path in chain:
        cycle = " -> ".join(p.name for p in (*chain, path))
        raise ValueError(f"Sidecar inheritance cycle detected: {cycle}")
    if not path.exists():
        raise FileNotFoundError(f"Sidecar file not found: {path}")

    payload = _read_yaml(path)
    config = _parse_sidecar_payload(payload)

    if config.inherits:
        base_path = (path.parent / config.inherits).resolve()
        if not base_path.exists():
            raise FileNotFoundError(f"Inherited sidecar not found: {base_path}")
        base_config = _load_sidecar(base_path, chain=(*chain, path))
        from markdown_docx_compiler.resolve.merge import merge_sidecar_config

        config = merge_sidecar_config(base_config, config)

    return config
