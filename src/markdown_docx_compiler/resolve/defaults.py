"""Built-in default values for the document compiler.

These defaults provide a sensible out-of-the-box appearance when no
sidecar is supplied.  They form tier 0 of the cascade (underneath the
sidecar's own ``document`` and ``defaults`` sections).
"""

from __future__ import annotations

from markdown_docx_compiler.models.config import (
    DocumentConfig,
    MarginConfig,
    PageConfig,
    RegionStyle,
)
from markdown_docx_compiler.models.style import (
    BlockStyle,
    BorderSide,
    BorderStyle,
    FontStyle,
    ImageProps,
    LinkStyle,
    SpacingStyle,
    TableProps,
)

# ---------------------------------------------------------------------------
# Document globals
# ---------------------------------------------------------------------------

DEFAULT_DOCUMENT = DocumentConfig(
    font=FontStyle(family="Aptos", size=10.5, color="111827"),
    mono_font="Consolas",
    link=LinkStyle(color="2563EB", underline=True),
    page=PageConfig(
        width_inches=8.5,
        margin=MarginConfig(top=1.0, bottom=0.8, left=1.0, right=1.0),
    ),
)

# ---------------------------------------------------------------------------
# Region styling
# ---------------------------------------------------------------------------

DEFAULT_PAGE_HEADER = RegionStyle(
    font=FontStyle(size=8.0, color="6B7280"),
)

DEFAULT_PAGE_FOOTER = RegionStyle(
    font=FontStyle(size=8.0, color="6B7280"),
    border=BorderStyle(top=BorderSide(color="D1D5DB", width=1.0, style="single")),
)

DEFAULT_DOC_HEADER = RegionStyle(
    font=FontStyle(size=9.0, color="6B7280"),
    image=ImageProps(width="0.7in"),
)

# ---------------------------------------------------------------------------
# Block-type defaults
# ---------------------------------------------------------------------------

DEFAULT_BLOCK_STYLES: dict[str, BlockStyle] = {
    "heading": BlockStyle(
        font=FontStyle(bold=True, color="1F2937"),
    ),
    "paragraph": BlockStyle(
        spacing=SpacingStyle(after=6.0, line=1.25),
    ),
    "table": BlockStyle(
        table=TableProps(header_row=True, border_color="D1D5DB"),
    ),
    "code": BlockStyle(
        font=FontStyle(size=9.5),
        background="F3F4F6",
        spacing=SpacingStyle(before=6.0, after=6.0, line=1.15),
    ),
    "blockquote": BlockStyle(
        font=FontStyle(italic=True, color="6B7280"),
        border=BorderStyle(left=BorderSide(color="94A3B8", width=3.0, style="single")),
        spacing=SpacingStyle(before=8.0, after=8.0, indent_left=0.3),
    ),
    "image": BlockStyle(
        image=ImageProps(alignment="center"),
        spacing=SpacingStyle(before=8.0, after=8.0),
    ),
    "list": BlockStyle(
        spacing=SpacingStyle(before=2.0, after=2.0),
    ),
}
