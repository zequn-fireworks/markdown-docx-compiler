"""Tests for selectors.py — block_type_name, rule matching, document-from-front-matter."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.ir import (
    BlockMeta,
    BlockQuoteBlock,
    CodeBlock,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    ListBlock,
    ListItem,
    ParagraphBlock,
    TableBlock,
    TableCell,
    Text,
)
from markdown_docx_compiler.selectors import (
    _document_from_front_matter,
    _resolve_optional_path,
    _rule_matches,
    block_type_name,
    resolve_block_style,
    resolve_document_config,
)
from markdown_docx_compiler.sidecar import (
    BlockStyle,
    DocumentConfig,
    SelectorMatch,
    SelectorRule,
    SidecarConfig,
)


class TestBlockTypeName:
    @pytest.mark.parametrize(
        ("block", "expected"),
        [
            (HeadingBlock(level=1, content=[Text("H")]), "heading"),
            (ParagraphBlock(content=[Text("P")]), "paragraph"),
            (HorizontalRuleBlock(), "horizontal_rule"),
            (CodeBlock(value="x"), "code"),
            (ImageBlock(path="/img.png"), "image"),
            (BlockQuoteBlock(content=[Text("Q")]), "blockquote"),
            (
                TableBlock(
                    headers=[TableCell(content=[Text("A")])],
                    rows=[],
                    alignments=["left"],
                ),
                "table",
            ),
            (ListBlock(ordered=False, items=[ListItem(blocks=[])]), "list"),
        ],
    )
    def test_known_types(self, block: object, expected: str) -> None:
        assert block_type_name(block) == expected  # type: ignore[arg-type]


class TestRuleMatches:
    def _para(self, **meta_kwargs: object) -> ParagraphBlock:
        return ParagraphBlock(content=[Text("text")], meta=BlockMeta(**meta_kwargs))  # type: ignore[arg-type]

    def test_empty_rule_matches_anything(self) -> None:
        assert _rule_matches(block=self._para(), rule=SelectorMatch()) is True

    def test_type_match(self) -> None:
        assert _rule_matches(block=self._para(), rule=SelectorMatch(type="paragraph")) is True

    def test_type_mismatch(self) -> None:
        assert _rule_matches(block=self._para(), rule=SelectorMatch(type="table")) is False

    def test_anchor_match(self) -> None:
        block = self._para(anchor="my-block")
        assert _rule_matches(block=block, rule=SelectorMatch(anchor="my-block")) is True

    def test_anchor_mismatch(self) -> None:
        block = self._para(anchor="my-block")
        assert _rule_matches(block=block, rule=SelectorMatch(anchor="other")) is False

    def test_index_match(self) -> None:
        block = self._para(index=3)
        assert _rule_matches(block=block, rule=SelectorMatch(index=3)) is True

    def test_index_mismatch(self) -> None:
        block = self._para(index=3)
        assert _rule_matches(block=block, rule=SelectorMatch(index=5)) is False

    def test_heading_match_in_path(self) -> None:
        block = self._para(heading_path=("Introduction", "Details"))
        assert _rule_matches(block=block, rule=SelectorMatch(heading="Details")) is True

    def test_heading_not_in_path(self) -> None:
        block = self._para(heading_path=("Introduction",))
        assert _rule_matches(block=block, rule=SelectorMatch(heading="Conclusion")) is False

    def test_heading_empty_path_fails(self) -> None:
        block = self._para()
        assert _rule_matches(block=block, rule=SelectorMatch(heading="Any")) is False

    def test_heading_document_matches_index_1(self) -> None:
        block = self._para(heading_path=("Title",), index=1)
        assert _rule_matches(block=block, rule=SelectorMatch(heading="__document__")) is True

    def test_heading_document_rejects_index_2(self) -> None:
        block = self._para(heading_path=("Title",), index=2)
        assert _rule_matches(block=block, rule=SelectorMatch(heading="__document__")) is False

    def test_column_count_match(self) -> None:
        table = TableBlock(
            headers=[TableCell(content=[Text("A")]), TableCell(content=[Text("B")])],
            rows=[],
            alignments=["left", "left"],
        )
        assert _rule_matches(block=table, rule=SelectorMatch(column_count=2)) is True

    def test_column_count_mismatch(self) -> None:
        table = TableBlock(
            headers=[TableCell(content=[Text("A")])],
            rows=[],
            alignments=["left"],
        )
        assert _rule_matches(block=table, rule=SelectorMatch(column_count=3)) is False

    def test_column_count_on_non_table_fails(self) -> None:
        block = self._para()
        assert _rule_matches(block=block, rule=SelectorMatch(column_count=2)) is False


class TestDocumentFromFrontMatter:
    def test_empty_front_matter(self) -> None:
        config = _document_from_front_matter({})
        assert config.font is None

    def test_extracts_standard_fields(self) -> None:
        data = {
            "title": "My Report",
            "font": "Arial",
            "mono_font": "Menlo",
            "primary_color": "FF0000",
        }
        config = _document_from_front_matter(data)
        assert config.title == "My Report"
        assert config.font == "Arial"
        assert config.mono_font == "Menlo"
        assert config.primary_color == "FF0000"

    def test_extracts_footer_from_flat_keys(self) -> None:
        data = {"footer_left": "Left", "footer_center": "Center", "footer_right": "Right"}
        config = _document_from_front_matter(data)
        assert config.footer.left == "Left"
        assert config.footer.center == "Center"
        assert config.footer.right == "Right"

    def test_extracts_footer_from_nested_dict(self) -> None:
        data = {"footer": {"left": "L", "center": "C", "right": "R"}}
        config = _document_from_front_matter(data)
        assert config.footer.left == "L"
        assert config.footer.center == "C"
        assert config.footer.right == "R"

    def test_extracts_margin(self) -> None:
        data = {"margin_top_inches": 1.5, "margin_left_inches": 0.8}
        config = _document_from_front_matter(data)
        assert config.margin.top_inches == 1.5
        assert config.margin.left_inches == 0.8


class TestResolveOptionalPath:
    def test_absolute_path_unchanged(self, tmp_path: Path) -> None:
        result = _resolve_optional_path("/absolute/logo.png", base_dir=tmp_path)
        assert result == "/absolute/logo.png"

    def test_relative_path_resolved_against_base(self, tmp_path: Path) -> None:
        result = _resolve_optional_path("images/logo.png", base_dir=tmp_path)
        assert result == str((tmp_path / "images/logo.png").resolve())


class TestResolveDocumentConfig:
    def test_template_from_front_matter(self) -> None:
        theme, _config, _sidecar = resolve_document_config(
            front_matter={"template": "fireworks"},
            sidecar=SidecarConfig(),
            base_dir=Path("."),
        )
        assert theme.name == "fireworks"

    def test_default_theme_when_unspecified(self) -> None:
        theme, _config, _sidecar = resolve_document_config(
            front_matter={},
            sidecar=SidecarConfig(),
            base_dir=Path("."),
        )
        assert theme.name == "default"

    def test_cli_overrides_applied(self) -> None:
        _, config, _sidecar = resolve_document_config(
            front_matter={},
            sidecar=SidecarConfig(),
            cli_overrides=DocumentConfig(font="Comic Sans"),
            base_dir=Path("."),
        )
        assert config.font == "Comic Sans"


class TestResolveBlockStyle:
    def test_layout_defaults_applied(self) -> None:
        from markdown_docx_compiler.styles.themes import _DEFAULT_LAYOUT, DEFAULT_THEME

        block = ParagraphBlock(content=[Text("text")])
        style = resolve_block_style(block=block, sidecar=_DEFAULT_LAYOUT, theme=DEFAULT_THEME)
        assert style.line_spacing == 1.25

    def test_sidecar_block_override_by_anchor(self) -> None:
        from markdown_docx_compiler.sidecar import merge_sidecar_config
        from markdown_docx_compiler.styles.themes import _DEFAULT_LAYOUT, DEFAULT_THEME

        block = ParagraphBlock(content=[Text("text")], meta=BlockMeta(anchor="special"))
        sidecar = merge_sidecar_config(_DEFAULT_LAYOUT, SidecarConfig(blocks={"special": BlockStyle(font_size=14.0)}))
        style = resolve_block_style(block=block, sidecar=sidecar, theme=DEFAULT_THEME)
        assert style.font_size == 14.0

    def test_selector_rule_applied(self) -> None:
        from markdown_docx_compiler.sidecar import merge_sidecar_config
        from markdown_docx_compiler.styles.themes import _DEFAULT_LAYOUT, DEFAULT_THEME

        block = ParagraphBlock(content=[Text("text")], meta=BlockMeta(index=1))
        rule = SelectorRule(match=SelectorMatch(type="paragraph"), apply=BlockStyle(bold=True))
        sidecar = merge_sidecar_config(_DEFAULT_LAYOUT, SidecarConfig(selectors=[rule]))
        style = resolve_block_style(block=block, sidecar=sidecar, theme=DEFAULT_THEME)
        assert style.bold is True
