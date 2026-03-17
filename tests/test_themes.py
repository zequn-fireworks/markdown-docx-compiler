"""Tests for styles/themes.py — theme structure and template lookup."""

from __future__ import annotations

from markdown_docx_compiler.styles.themes import _DEFAULT_LAYOUT, DEFAULT_THEME, Theme, get_template


class TestDefaultTheme:
    def test_name(self) -> None:
        assert DEFAULT_THEME.name == "default"

    def test_has_required_document_fields(self) -> None:
        assert DEFAULT_THEME.document.font
        assert DEFAULT_THEME.document.mono_font
        assert DEFAULT_THEME.document.primary_color
        assert DEFAULT_THEME.document.text_color

    def test_has_paragraph_variants(self) -> None:
        assert "body" in DEFAULT_THEME.variants.get("paragraph", {})
        assert "lead" in DEFAULT_THEME.variants.get("paragraph", {})

    def test_has_table_variants(self) -> None:
        assert "standard" in DEFAULT_THEME.variants.get("table", {})
        assert "benchmark" in DEFAULT_THEME.variants.get("table", {})

    def test_default_margin(self) -> None:
        margin = DEFAULT_THEME.document.margin
        assert margin.top_inches == 1.0
        assert margin.bottom_inches == 0.8
        assert margin.left_inches == 1.0
        assert margin.right_inches == 1.0

    def test_default_page_width(self) -> None:
        assert DEFAULT_THEME.document.page_width_inches == 8.5

    def test_no_defaults_on_theme(self) -> None:
        assert not hasattr(DEFAULT_THEME, "defaults")


class TestDefaultLayout:
    def test_has_standard_block_defaults(self) -> None:
        expected = {"paragraph", "table", "code", "blockquote", "list", "image"}
        assert set(_DEFAULT_LAYOUT.defaults.keys()) == expected

    def test_paragraph_default_has_variant(self) -> None:
        assert _DEFAULT_LAYOUT.defaults["paragraph"].variant == "body"

    def test_paragraph_default_has_line_spacing(self) -> None:
        assert _DEFAULT_LAYOUT.defaults["paragraph"].line_spacing == 1.25


class TestGetTemplate:
    def test_default_returns_builtin(self) -> None:
        result = get_template("default")
        assert result is not None
        theme, sidecar = result
        assert theme is DEFAULT_THEME
        assert sidecar is _DEFAULT_LAYOUT

    def test_unknown_returns_none(self) -> None:
        assert get_template("nonexistent") is None


class TestThemeDataclass:
    def test_frozen(self) -> None:
        theme = Theme(name="test", document=DEFAULT_THEME.document)
        try:
            theme.name = "modified"  # type: ignore[misc]
            raise AssertionError("Should not be mutable")
        except AttributeError:
            pass
