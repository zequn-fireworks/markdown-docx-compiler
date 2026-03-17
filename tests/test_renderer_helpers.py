"""Tests for renderer.py helper functions and RenderContext."""

from __future__ import annotations

import pytest

from markdown_docx_compiler.backend.docx.renderer import (
    RenderContext,
    _auto_column_widths,
    _parse_column_widths,
    _stringify_inline,
    _strip_markers,
)
from markdown_docx_compiler.ir import (
    CodeSpan,
    Emphasis,
    LineBreak,
    Link,
    Strike,
    Strong,
    TableBlock,
    TableCell,
    Text,
)
from markdown_docx_compiler.sidecar import DocumentConfig, MarginConfig
from markdown_docx_compiler.styles.themes import DEFAULT_THEME


class TestStringifyInline:
    def test_plain_text(self) -> None:
        assert _stringify_inline([Text("hello")]) == "hello"

    def test_code_span(self) -> None:
        assert _stringify_inline([CodeSpan("code")]) == "code"

    def test_strong(self) -> None:
        assert _stringify_inline([Strong([Text("bold")])]) == "bold"

    def test_emphasis(self) -> None:
        assert _stringify_inline([Emphasis([Text("italic")])]) == "italic"

    def test_strike(self) -> None:
        assert _stringify_inline([Strike([Text("struck")])]) == "struck"

    def test_link(self) -> None:
        assert _stringify_inline([Link(url="http://x", children=[Text("label")])]) == "label"

    def test_line_break(self) -> None:
        assert _stringify_inline([Text("a"), LineBreak(), Text("b")]) == "a\nb"

    def test_nested(self) -> None:
        nodes = [Text("A "), Strong([Text("B"), Emphasis([Text("C")])])]
        assert _stringify_inline(nodes) == "A BC"

    def test_empty(self) -> None:
        assert _stringify_inline([]) == ""


class TestStripMarkers:
    def test_collapses_whitespace(self) -> None:
        assert _strip_markers("  hello   world  ") == "hello world"

    def test_newlines_collapsed(self) -> None:
        assert _strip_markers("a\n\n  b") == "a b"

    def test_empty_string(self) -> None:
        assert _strip_markers("") == ""


class TestParseColumnWidths:
    TOTAL = 9360  # typical content width in twips (6.5in * 1440)

    def test_fr_units_equal(self) -> None:
        widths = _parse_column_widths(["1fr", "1fr", "1fr"], total=self.TOTAL, columns=3)
        assert len(widths) == 3
        assert sum(widths) == self.TOTAL
        assert abs(widths[0] - widths[1]) <= 1

    def test_fr_units_weighted(self) -> None:
        widths = _parse_column_widths(["3fr", "1fr"], total=self.TOTAL, columns=2)
        assert sum(widths) == self.TOTAL
        assert widths[0] > widths[1]
        ratio = widths[0] / widths[1]
        assert abs(ratio - 3.0) < 0.1

    def test_percent_units(self) -> None:
        widths = _parse_column_widths(["50%", "50%"], total=self.TOTAL, columns=2)
        assert sum(widths) == self.TOTAL

    def test_inch_units(self) -> None:
        widths = _parse_column_widths(["2in", "1fr"], total=self.TOTAL, columns=2)
        assert widths[0] == 2 * 1440
        assert sum(widths) == self.TOTAL

    def test_mixed_units(self) -> None:
        widths = _parse_column_widths(["2in", "50%", "1fr"], total=self.TOTAL, columns=3)
        assert widths[0] == 2880
        assert sum(widths) == self.TOTAL

    def test_pads_missing_specs(self) -> None:
        widths = _parse_column_widths(["2fr"], total=self.TOTAL, columns=3)
        assert len(widths) == 3
        assert sum(widths) == self.TOTAL

    def test_truncates_excess_specs(self) -> None:
        widths = _parse_column_widths(["1fr", "1fr", "1fr", "1fr"], total=self.TOTAL, columns=2)
        assert len(widths) == 2
        assert sum(widths) == self.TOTAL

    def test_bare_number_treated_as_fr(self) -> None:
        widths = _parse_column_widths(["abc", "1fr"], total=self.TOTAL, columns=2)
        assert len(widths) == 2
        assert sum(widths) == self.TOTAL


class TestAutoColumnWidths:
    def test_equal_content(self) -> None:
        total = 9360
        block = TableBlock(
            headers=[TableCell(content=[Text("AA")]), TableCell(content=[Text("BB")])],
            rows=[[TableCell(content=[Text("xx")]), TableCell(content=[Text("yy")])]],
            alignments=["left", "left"],
        )
        widths = _auto_column_widths(block=block, total=total)
        assert len(widths) == 2
        assert sum(widths) == total
        assert abs(widths[0] - widths[1]) <= 1

    def test_unequal_content(self) -> None:
        total = 9360
        block = TableBlock(
            headers=[TableCell(content=[Text("Short")]), TableCell(content=[Text("A much longer header")])],
            rows=[],
            alignments=["left", "left"],
        )
        widths = _auto_column_widths(block=block, total=total)
        assert widths[1] > widths[0]
        assert sum(widths) == total


class TestRenderContext:
    def test_content_width_default(self) -> None:
        ctx = RenderContext(
            theme=DEFAULT_THEME,
            config=DocumentConfig(
                page_width_inches=8.5,
                margin=MarginConfig(left_inches=1.0, right_inches=1.0),
            ),
        )
        assert ctx.content_width_inches == pytest.approx(6.5)
        assert ctx.content_width_twips == 9360

    def test_content_width_custom_margins(self) -> None:
        ctx = RenderContext(
            theme=DEFAULT_THEME,
            config=DocumentConfig(
                page_width_inches=11.0,
                margin=MarginConfig(left_inches=0.5, right_inches=0.5),
            ),
        )
        assert ctx.content_width_inches == pytest.approx(10.0)

    def test_content_width_none_uses_defaults(self) -> None:
        ctx = RenderContext(theme=DEFAULT_THEME, config=DocumentConfig())
        assert ctx.content_width_inches == pytest.approx(6.5)
