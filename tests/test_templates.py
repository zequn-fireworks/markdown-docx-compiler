"""Tests for template loading, brand parsing, sidecar merging, and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.selectors import resolve_document_config
from markdown_docx_compiler.sidecar import (
    BlockStyle,
    DocumentConfig,
    FooterConfig,
    SelectorMatch,
    SelectorRule,
    SidecarConfig,
    _parse_sidecar_payload,
    merge_sidecar_config,
)
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
# parse_sidecar_payload (extracted for template layout loading)
# ---------------------------------------------------------------------------


class TestParseSidecarPayload:
    def test_reads_template_field(self) -> None:
        config = _parse_sidecar_payload({"template": "fireworks-rca"})
        assert config.template == "fireworks-rca"

    def test_template_none_when_absent(self) -> None:
        config = _parse_sidecar_payload({})
        assert config.template is None


# ---------------------------------------------------------------------------
# merge_sidecar_config
# ---------------------------------------------------------------------------


class TestMergeSidecarConfig:
    def test_document_merge(self) -> None:
        base = SidecarConfig(document=DocumentConfig(font="Arial", footer=FooterConfig(left="Base")))
        override = SidecarConfig(document=DocumentConfig(footer=FooterConfig(left="Override")))
        merged = merge_sidecar_config(base, override)
        assert merged.document.font == "Arial"
        assert merged.document.footer.left == "Override"

    def test_defaults_merge(self) -> None:
        base = SidecarConfig(
            defaults={
                "paragraph": BlockStyle(variant="body", line_spacing=1.25),
                "table": BlockStyle(variant="standard"),
            }
        )
        override = SidecarConfig(
            defaults={
                "paragraph": BlockStyle(line_spacing=1.5),
                "code": BlockStyle(font_size=10.0),
            }
        )
        merged = merge_sidecar_config(base, override)
        assert merged.defaults["paragraph"].variant == "body"
        assert merged.defaults["paragraph"].line_spacing == 1.5
        assert merged.defaults["table"].variant == "standard"
        assert merged.defaults["code"].font_size == 10.0

    def test_selectors_concatenated(self) -> None:
        rule1 = SelectorRule(match=SelectorMatch(type="paragraph"), apply=BlockStyle(bold=True))
        rule2 = SelectorRule(match=SelectorMatch(type="table"), apply=BlockStyle(width="full"))
        base = SidecarConfig(selectors=[rule1])
        override = SidecarConfig(selectors=[rule2])
        merged = merge_sidecar_config(base, override)
        assert len(merged.selectors) == 2
        assert merged.selectors[0].match.type == "paragraph"
        assert merged.selectors[1].match.type == "table"

    def test_blocks_merge(self) -> None:
        base = SidecarConfig(blocks={"my-table": BlockStyle(variant="standard", width="full")})
        override = SidecarConfig(
            blocks={
                "my-table": BlockStyle(columns=["3fr", "1fr"]),
                "new-block": BlockStyle(bold=True),
            }
        )
        merged = merge_sidecar_config(base, override)
        assert merged.blocks["my-table"].variant == "standard"
        assert merged.blocks["my-table"].columns == ["3fr", "1fr"]
        assert merged.blocks["new-block"].bold is True

    def test_template_from_override_wins(self) -> None:
        base = SidecarConfig(template="base-template")
        override = SidecarConfig(template="override-template")
        merged = merge_sidecar_config(base, override)
        assert merged.template == "override-template"

    def test_template_falls_back_to_base(self) -> None:
        base = SidecarConfig(template="base-template")
        override = SidecarConfig()
        merged = merge_sidecar_config(base, override)
        assert merged.template == "base-template"


# ---------------------------------------------------------------------------
# Entry-point discovery (using actually installed fireworks package)
# ---------------------------------------------------------------------------


class TestTemplateDiscovery:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        _reset_template_cache()
        yield
        _reset_template_cache()

    def test_fireworks_default_template_discovered(self) -> None:
        result = get_template("fireworks")
        assert result is not None
        theme, sidecar = result
        assert theme.name == "fireworks"
        assert theme.document.font == "Helvetica Neue"
        assert sidecar.defaults.get("paragraph") is not None

    def test_fireworks_rca_template_discovered(self) -> None:
        result = get_template("fireworks-rca")
        assert result is not None
        theme, sidecar = result
        assert theme.name == "fireworks"
        assert len(sidecar.selectors) >= 1

    def test_unknown_template_returns_none(self) -> None:
        assert get_template("nonexistent-template") is None

    def test_brand_variants_loaded(self) -> None:
        result = get_template("fireworks")
        assert result is not None
        theme, _ = result
        assert "paragraph" in theme.variants
        assert "lead" in theme.variants["paragraph"]
        assert "table" in theme.variants
        assert "benchmark" in theme.variants["table"]

    def test_brand_logo_is_none(self) -> None:
        result = get_template("fireworks")
        assert result is not None
        theme, _ = result
        assert theme.document.logo_path is None

    def test_template_layout_has_footer(self) -> None:
        result = get_template("fireworks")
        assert result is not None
        _, sidecar = result
        assert sidecar.document.footer.left == "Fireworks AI  |  Confidential"


# ---------------------------------------------------------------------------
# Resolution with templates
# ---------------------------------------------------------------------------


class TestResolveWithTemplate:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        _reset_template_cache()
        yield
        _reset_template_cache()

    def test_template_from_sidecar(self) -> None:
        sidecar = SidecarConfig(template="fireworks-rca")
        theme, config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=sidecar,
            base_dir=Path("."),
        )
        assert theme.name == "fireworks"
        assert config.font == "Helvetica Neue"
        assert config.footer.left == "Fireworks AI  |  Confidential"

    def test_template_from_front_matter(self) -> None:
        theme, config, _resolved = resolve_document_config(
            front_matter={"template": "fireworks"},
            sidecar=SidecarConfig(),
            base_dir=Path("."),
        )
        assert theme.name == "fireworks"
        assert config.font == "Helvetica Neue"

    def test_template_from_cli_override(self) -> None:
        theme, _config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=SidecarConfig(),
            template_override="fireworks",
            base_dir=Path("."),
        )
        assert theme.name == "fireworks"

    def test_user_sidecar_overrides_template_footer(self) -> None:
        sidecar = SidecarConfig(
            template="fireworks",
            document=DocumentConfig(footer=FooterConfig(center="2026-03-16", right="Draft")),
        )
        _theme, config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=sidecar,
            base_dir=Path("."),
        )
        assert config.footer.left == "Fireworks AI  |  Confidential"
        assert config.footer.center == "2026-03-16"
        assert config.footer.right == "Draft"

    def test_user_sidecar_overrides_template_defaults(self) -> None:
        sidecar = SidecarConfig(
            template="fireworks",
            defaults={"paragraph": BlockStyle(line_spacing=1.5)},
        )
        _theme, _config, resolved = resolve_document_config(
            front_matter={},
            sidecar=sidecar,
            base_dir=Path("."),
        )
        assert resolved.defaults["paragraph"].line_spacing == 1.5
        assert resolved.defaults["paragraph"].variant == "body"

    def test_user_logo_overrides_null_template_logo(self) -> None:
        sidecar = SidecarConfig(
            template="fireworks",
            document=DocumentConfig(logo_path="/abs/path/logo.png"),
        )
        _theme, config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=sidecar,
            base_dir=Path("."),
        )
        assert config.logo_path == "/abs/path/logo.png"

    def test_unknown_template_falls_back_to_default_theme(self) -> None:
        sidecar = SidecarConfig(template="nonexistent")
        theme, _config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=sidecar,
            base_dir=Path("."),
        )
        assert theme.name == "default"

    def test_template_override_takes_priority(self) -> None:
        sidecar = SidecarConfig(template="nonexistent")
        theme, _config, _resolved = resolve_document_config(
            front_matter={"template": "also-nonexistent"},
            sidecar=sidecar,
            template_override="fireworks",
            base_dir=Path("."),
        )
        assert theme.name == "fireworks"


class TestNoTemplateUsesDefault:
    def test_no_template_uses_default(self) -> None:
        theme, _config, _resolved = resolve_document_config(
            front_matter={},
            sidecar=SidecarConfig(),
            base_dir=Path("."),
        )
        assert theme.name == "default"


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
        assert "uv add" in text

    def test_lists_discovered_templates(self) -> None:
        text = templates_help_topic()
        assert "fireworks" in text
