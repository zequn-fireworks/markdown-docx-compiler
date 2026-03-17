"""Tests for sidecar.py — YAML loading, internal parsers, and merge logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.sidecar import (
    BlockStyle,
    DocumentConfig,
    FooterConfig,
    MarginConfig,
    SidecarConfig,
    _block_style_from_dict,
    _document_from_dict,
    _footer_from_dict,
    _margin_from_dict,
    _read_yaml,
    _selector_from_dict,
    load_sidecar,
    merge_block_style,
    merge_document_config,
)


class TestReadYaml:
    def test_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "config.yaml"
        f.write_text("key: value\n")
        assert _read_yaml(f) == {"key": "value"}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert _read_yaml(f) == {}

    def test_non_mapping_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(ValueError, match="must be a mapping"):
            _read_yaml(f)


class TestMarginFromDict:
    def test_none_input(self) -> None:
        result = _margin_from_dict(None)
        assert result == MarginConfig()

    def test_standard_keys(self) -> None:
        result = _margin_from_dict({"top_inches": 1.5, "bottom_inches": 0.8})
        assert result.top_inches == 1.5
        assert result.bottom_inches == 0.8

    def test_short_keys(self) -> None:
        result = _margin_from_dict({"top": 2.0, "left": 0.5})
        assert result.top_inches == 2.0
        assert result.left_inches == 0.5


class TestFooterFromDict:
    def test_none_input(self) -> None:
        assert _footer_from_dict(None) == FooterConfig()

    def test_full_footer(self) -> None:
        result = _footer_from_dict({"left": "L", "center": "C", "right": "R", "show_page_numbers": True})
        assert result.left == "L"
        assert result.center == "C"
        assert result.right == "R"
        assert result.show_page_numbers is True


class TestDocumentFromDict:
    def test_none_input(self) -> None:
        config = _document_from_dict(None)
        assert config == DocumentConfig()

    def test_full_document(self) -> None:
        data = {
            "font": "Arial",
            "mono_font": "Menlo",
            "primary_color": "6720FF",
            "margin": {"top_inches": 1.5},
            "footer": {"left": "Footer"},
        }
        config = _document_from_dict(data)
        assert config.font == "Arial"
        assert config.margin.top_inches == 1.5
        assert config.footer.left == "Footer"


class TestBlockStyleFromDict:
    def test_none_input(self) -> None:
        assert _block_style_from_dict(None) == BlockStyle()

    def test_full_block_style(self) -> None:
        data = {
            "variant": "benchmark",
            "width": "full",
            "columns": ["3fr", "1fr"],
            "font_size": 12.0,
            "bold": True,
            "italic": False,
            "color": "FF0000",
            "background_color": "EEEEEE",
            "border_color": "CCCCCC",
            "line_spacing": 1.5,
            "space_before": 4.0,
            "space_after": 8.0,
            "page_break_before": True,
        }
        result = _block_style_from_dict(data)
        assert result.variant == "benchmark"
        assert result.columns == ["3fr", "1fr"]
        assert result.bold is True
        assert result.page_break_before is True


class TestSelectorFromDict:
    def test_none_input(self) -> None:
        from markdown_docx_compiler.sidecar import SelectorMatch

        assert _selector_from_dict(None) == SelectorMatch()

    def test_full_selector(self) -> None:
        data = {"type": "table", "heading": "Results", "index": 3, "anchor": "t1", "column_count": 4}
        result = _selector_from_dict(data)
        assert result.type == "table"
        assert result.heading == "Results"
        assert result.index == 3
        assert result.anchor == "t1"
        assert result.column_count == 4


class TestLoadSidecar:
    def test_none_path(self) -> None:
        assert load_sidecar(None) == SidecarConfig()

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        assert load_sidecar(tmp_path / "missing.yaml") == SidecarConfig()

    def test_full_sidecar(self, tmp_path: Path) -> None:
        f = tmp_path / "spec.yaml"
        f.write_text(
            "document:\n"
            "  font: Helvetica\n"
            "defaults:\n"
            "  paragraph:\n"
            "    line_spacing: 1.4\n"
            "selectors:\n"
            "  - match:\n"
            "      type: paragraph\n"
            "    apply:\n"
            "      bold: true\n"
            "blocks:\n"
            "  my-table:\n"
            "    variant: benchmark\n"
            "    columns: ['3fr', '1fr']\n"
        )
        config = load_sidecar(f)
        assert config.document.font == "Helvetica"
        assert config.defaults["paragraph"].line_spacing == 1.4
        assert len(config.selectors) == 1
        assert config.selectors[0].match.type == "paragraph"
        assert config.selectors[0].apply.bold is True
        assert config.blocks["my-table"].variant == "benchmark"
        assert config.blocks["my-table"].columns == ["3fr", "1fr"]

    def test_non_dict_selector_items_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "spec.yaml"
        f.write_text("selectors:\n  - not_a_dict\n  - match:\n      type: table\n    apply:\n      bold: true\n")
        config = load_sidecar(f)
        assert len(config.selectors) == 1


class TestMergeDocumentConfig:
    def test_override_replaces_non_null(self) -> None:
        base = DocumentConfig(font="Aptos", text_color="111827")
        override = DocumentConfig(font="Arial")
        result = merge_document_config(base, override)
        assert result.font == "Arial"
        assert result.text_color == "111827"

    def test_null_override_preserves_base(self) -> None:
        base = DocumentConfig(font="Aptos")
        override = DocumentConfig()
        result = merge_document_config(base, override)
        assert result.font == "Aptos"

    def test_margin_merge(self) -> None:
        base = DocumentConfig(margin=MarginConfig(top_inches=1.0, left_inches=1.0))
        override = DocumentConfig(margin=MarginConfig(top_inches=1.5))
        result = merge_document_config(base, override)
        assert result.margin.top_inches == 1.5
        assert result.margin.left_inches == 1.0

    def test_footer_merge(self) -> None:
        base = DocumentConfig(footer=FooterConfig(left="Base", right="R"))
        override = DocumentConfig(footer=FooterConfig(left="Override"))
        result = merge_document_config(base, override)
        assert result.footer.left == "Override"
        assert result.footer.right == "R"

    def test_page_width_override(self) -> None:
        base = DocumentConfig(page_width_inches=8.5)
        override = DocumentConfig(page_width_inches=11.0)
        result = merge_document_config(base, override)
        assert result.page_width_inches == 11.0

    def test_show_page_numbers_merge(self) -> None:
        base = DocumentConfig(footer=FooterConfig(show_page_numbers=True))
        override = DocumentConfig(footer=FooterConfig(show_page_numbers=False))
        result = merge_document_config(base, override)
        assert result.footer.show_page_numbers is False


class TestMergeBlockStyle:
    def test_override_replaces_non_null(self) -> None:
        base = BlockStyle(variant="body", font_size=10.0)
        override = BlockStyle(font_size=12.0)
        result = merge_block_style(base, override)
        assert result.variant == "body"
        assert result.font_size == 12.0

    def test_null_override_preserves_base(self) -> None:
        base = BlockStyle(bold=True, color="FF0000")
        override = BlockStyle()
        result = merge_block_style(base, override)
        assert result.bold is True
        assert result.color == "FF0000"

    def test_full_override(self) -> None:
        base = BlockStyle(variant="a", bold=False)
        override = BlockStyle(variant="b", bold=True)
        result = merge_block_style(base, override)
        assert result.variant == "b"
        assert result.bold is True
