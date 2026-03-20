"""Hierarchical style property models.

Every property is nullable — ``None`` means "inherit from the next tier in the
cascade."  Property groups are composed into a single ``BlockStyle`` that can
describe any block element.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Property groups
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FontStyle:
    """Typographic properties applied to text runs."""

    family: str | None = None
    size: float | None = None  # pt
    color: str | None = None  # hex without '#'
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    strikethrough: bool | None = None
    small_caps: bool | None = None
    all_caps: bool | None = None
    letter_spacing: float | None = None  # pt
    highlight: str | None = None  # hex highlight color


@dataclass(frozen=True)
class SpacingStyle:
    """Whitespace properties on a block container."""

    before: float | None = None  # pt
    after: float | None = None  # pt
    line: float | None = None  # multiplier (1.0, 1.15, 1.5 …)
    indent_left: float | None = None  # inches
    indent_right: float | None = None  # inches
    indent_first_line: float | None = None  # inches


@dataclass(frozen=True)
class BorderSide:
    """Visual properties for one side of a border."""

    color: str | None = None  # hex
    width: float | None = None  # pt
    style: str | None = None  # single | double | dotted | dashed | none


@dataclass(frozen=True)
class BorderStyle:
    """Four-sided border specification."""

    top: BorderSide | None = None
    bottom: BorderSide | None = None
    left: BorderSide | None = None
    right: BorderSide | None = None


@dataclass(frozen=True)
class LinkStyle:
    """Hyperlink appearance."""

    color: str | None = None
    underline: bool | None = None


@dataclass(frozen=True)
class PaddingStyle:
    """Inner padding (used for table cells)."""

    top: float | None = None  # pt
    bottom: float | None = None
    left: float | None = None
    right: float | None = None


@dataclass(frozen=True)
class ImageProps:
    """Image-specific layout properties."""

    width: str | None = None  # "3in", "50%", "auto"
    alignment: str | None = None  # left | center | right


@dataclass(frozen=True)
class ListProps:
    """Ordered-list numbering properties."""

    numbering: str | None = None  # decimal_hierarchical | alpha_hierarchical | alpha_paren_hierarchical


@dataclass(frozen=True)
class TableProps:
    """Table-specific layout and visual properties."""

    columns: list[str] | None = None  # ["1fr", "3fr"] or ["2in", "50%"]
    header_row: bool | None = None  # default True; False hides header styling
    alternating_color: str | None = None  # hex for even-row shading
    cell_padding: PaddingStyle | None = None
    border_color: str | None = None  # shorthand for uniform table borders


# ---------------------------------------------------------------------------
# Composite block style
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockStyle:
    """Complete style for a block element.

    Combines all property groups.  Type-specific groups (``table``,
    ``image``) are only meaningful for the corresponding block types but
    are carried uniformly to keep the cascade simple.
    """

    font: FontStyle | None = None
    spacing: SpacingStyle | None = None
    background: str | None = None  # hex
    border: BorderStyle | None = None
    alignment: str | None = None  # left | center | right | justify
    page_break_before: bool | None = None
    keep_with_next: bool | None = None
    width: str | None = None  # "full", "auto", or a measurement

    link: LinkStyle | None = None
    image: ImageProps | None = None
    list: ListProps | None = None
    table: TableProps | None = None
