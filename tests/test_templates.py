"""Tests for template loading, brand parsing, sidecar merging, and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.models.config import (
    BlockOverride,
    DocumentConfig,
    SidecarConfig,
)
from markdown_docx_compiler.models.loader import _parse_sidecar_payload
from markdown_docx_compiler.models.style import BlockStyle, FontStyle, SpacingStyle
from markdown_docx_compiler.resolve.cascade import resolve_document_config
from markdown_docx_compiler.resolve.merge import merge_sidecar_config
from markdown_docx_compiler.styles.themes import (
    _reset_template_cache,
    get_template,
    load_brand_yaml,
    templates_help_topic,
)

# ---------------------------------------------------------------------------
# Brand YAML loading
# ---------------------------------------------------------------------------


class TestLoadBrandYaml:
    def test_parses_name(self) -> None:
        theme = load_brand_yaml("name: acme\nfont: Arial\n")
        assert theme.name == "acme"

    def test_parses_document_config(self) -> None:
        text = (
            "name: acme\n"
            "font: Arial\n"
            "mono_font: Courier\n"
            "primary_color: '003366'\n"
            "text_color: '333333'\n"
            "muted_color: '666666'\n"
            "border_color: 'CCCCCC'\n"
            "page_width_inches: 8.5\n"
        )
        theme = load_brand_yaml(text)
        assert theme.document.font == "Arial"
        assert theme.document.mono_font == "Courier"
        assert theme.document.primary_color == "003366"
        assert theme.document.page_width_inches == 8.5

    def test_logo_null_becomes_none(self) -> None:
        theme = load_brand_yaml("name: acme\nlogo: null\n")
        assert theme.document.logo_path is None

    def test_logo_path_is_preserved(self) -> None:
        theme = load_brand_yaml("name: acme\nlogo: assets/logo.png\n")
        assert theme.document.logo_path == "assets/logo.png"

    def test_parses_variants(self) -> None:
        text = (
            "name: acme\n"
            "variants:\n"
            "  paragraph:\n"
            "    body: {}\n"
            "    lead:\n"
            "      font_size: 14.0\n"
            "  table:\n"
            "    standard:\n"
            "      background_color: 'F0F0F0'\n"
        )
        theme = load_brand_yaml(text)
        assert "body" in theme.variants["paragraph"]
        assert "lead" in theme.variants["paragraph"]
        assert theme.variants["paragraph"]["lead"].font_size == 14.0
        assert theme.variants["table"]["standard"].background_color == "F0F0F0"

    def test_empty_yaml_uses_unknown_name(self) -> None:
        theme = load_brand_yaml("")
        assert theme.name == "unknown"

    def test_non_mapping_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a mapping"):
            load_brand_yaml("- item1\n- item2\n")

    def test_theme_name_set_on_document(self) -> None:
        theme = load_brand_yaml("name: acme\n")
        assert theme.document.theme == "acme"


# ---------------------------------------------------------------------------
# _parse_sidecar_payload (new pipeline)
# ---------------------------------------------------------------------------


class TestParseSidecarPayload:
    def test_reads_extend_field(self) -> None:
        config = _parse_sidecar_payload({"extend": "acme-report"})
        assert config.extend == "acme-report"

    def test_extend_none_when_absent(self) -> None:
        config = _parse_sidecar_payload({})
        assert config.extend is None


# ---------------------------------------------------------------------------
# merge_sidecar_config (new pipeline)
# ---------------------------------------------------------------------------


class TestMergeSidecarConfig:
    def test_document_merge(self) -> None:
        base = SidecarConfig(
            document=DocumentConfig(font=FontStyle(family="Arial")),
        )
        override = SidecarConfig(
            document=DocumentConfig(title="Override Title"),
        )
        merged = merge_sidecar_config(base, override)
        assert merged.document.font.family == "Arial"
        assert merged.document.title == "Override Title"

    def test_defaults_merge(self) -> None:
        base = SidecarConfig(
            defaults={
                "paragraph": BlockStyle(spacing=SpacingStyle(line=1.25)),
                "table": BlockStyle(width="full"),
            }
        )
        override = SidecarConfig(
            defaults={
                "paragraph": BlockStyle(spacing=SpacingStyle(line=1.5)),
                "code": BlockStyle(font=FontStyle(size=10.0)),
            }
        )
        merged = merge_sidecar_config(base, override)
        assert merged.defaults["paragraph"].spacing.line == 1.5
        assert merged.defaults["table"].width == "full"
        assert merged.defaults["code"].font.size == 10.0

    def test_blocks_merge(self) -> None:
        base = SidecarConfig(
            blocks={
                "my-table": BlockOverride(type="table", style=BlockStyle(width="full")),
            }
        )
        override = SidecarConfig(
            blocks={
                "my-table": BlockOverride(
                    style=BlockStyle(table=None),
                ),
                "new-block": BlockOverride(style=BlockStyle(font=FontStyle(bold=True))),
            }
        )
        merged = merge_sidecar_config(base, override)
        assert merged.blocks["my-table"].type == "table"
        assert merged.blocks["my-table"].style.width == "full"
        assert merged.blocks["new-block"].style.font.bold is True

    def test_extend_from_override_wins(self) -> None:
        base = SidecarConfig(extend="base-template")
        override = SidecarConfig(extend="override-template")
        merged = merge_sidecar_config(base, override)
        assert merged.extend == "override-template"

    def test_extend_falls_back_to_base(self) -> None:
        base = SidecarConfig(extend="base-template")
        override = SidecarConfig()
        merged = merge_sidecar_config(base, override)
        assert merged.extend == "base-template"


# ---------------------------------------------------------------------------
# Entry-point discovery
# ---------------------------------------------------------------------------


class TestTemplateDiscovery:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        _reset_template_cache()
        yield
        _reset_template_cache()

    def test_default_template_always_available(self) -> None:
        result = get_template("default")
        assert result is not None
        theme, layout = result
        assert theme.name == "default"
        assert theme.document.font == "Aptos"
        assert layout.defaults.get("paragraph") is not None

    def test_unknown_template_returns_none(self) -> None:
        assert get_template("nonexistent-template") is None

    def test_default_brand_variants_loaded(self) -> None:
        result = get_template("default")
        assert result is not None
        theme, _ = result
        assert "paragraph" in theme.variants
        assert "lead" in theme.variants["paragraph"]
        assert "table" in theme.variants
        assert "benchmark" in theme.variants["table"]


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


class TestResolveDocumentConfig:
    def test_sidecar_overrides_defaults(self) -> None:
        sidecar = SidecarConfig(
            document=DocumentConfig(font=FontStyle(family="Courier")),
        )
        doc_config, _resolved = resolve_document_config(
            sidecar=sidecar,
            front_matter={},
            base_dir=Path("."),
        )
        assert doc_config.font.family == "Courier"

    def test_front_matter_overrides_sidecar(self) -> None:
        sidecar = SidecarConfig(
            document=DocumentConfig(font=FontStyle(family="Arial")),
        )
        doc_config, _ = resolve_document_config(
            sidecar=sidecar,
            front_matter={"font": "Times"},
            base_dir=Path("."),
        )
        assert doc_config.font.family == "Times"

    def test_empty_sidecar_uses_builtin_defaults(self) -> None:
        doc_config, _ = resolve_document_config(
            sidecar=SidecarConfig(),
            front_matter={},
            base_dir=Path("."),
        )
        assert doc_config.font.family is not None


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------


class TestTemplatesHelpTopic:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        _reset_template_cache()
        yield
        _reset_template_cache()

    def test_contains_install_instructions(self) -> None:
        text = templates_help_topic()
        assert "uv add" in text or "Install" in text

    def test_shows_none_installed_when_empty(self) -> None:
        text = templates_help_topic()
        assert "none installed" in text
