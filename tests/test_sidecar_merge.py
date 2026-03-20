"""Tests for sidecar parsing, inheritance, and merge behavior."""

from __future__ import annotations

import pytest

from markdown_docx_compiler.models.config import (
    BlockOverride,
    DocumentConfig,
    SidecarConfig,
)
from markdown_docx_compiler.models.loader import _parse_sidecar_payload, load_sidecar
from markdown_docx_compiler.models.style import BlockStyle, FontStyle, SpacingStyle
from markdown_docx_compiler.resolve.merge import merge_sidecar_config


class TestParseSidecarPayload:
    def test_reads_inherits_field(self) -> None:
        config = _parse_sidecar_payload({"inherits": "../base.docx.yaml"})
        assert config.inherits == "../base.docx.yaml"

    def test_inherits_none_when_absent(self) -> None:
        config = _parse_sidecar_payload({})
        assert config.inherits is None

    def test_unknown_top_level_key_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown sidecar top-level key"):
            _parse_sidecar_payload({"extend": "../base.docx.yaml"})


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
                    style=BlockStyle(background="EEEEEE"),
                ),
                "new-block": BlockOverride(style=BlockStyle(font=FontStyle(bold=True))),
            }
        )
        merged = merge_sidecar_config(base, override)
        assert merged.blocks["my-table"].type == "table"
        assert merged.blocks["my-table"].style.width == "full"
        assert merged.blocks["my-table"].style.background == "EEEEEE"
        assert merged.blocks["new-block"].style.font.bold is True

    def test_inherits_from_override_wins(self) -> None:
        base = SidecarConfig(inherits="../base.docx.yaml")
        override = SidecarConfig(inherits="./override.docx.yaml")
        merged = merge_sidecar_config(base, override)
        assert merged.inherits == "./override.docx.yaml"

    def test_inherits_falls_back_to_base(self) -> None:
        base = SidecarConfig(inherits="../base.docx.yaml")
        override = SidecarConfig()
        merged = merge_sidecar_config(base, override)
        assert merged.inherits == "../base.docx.yaml"


class TestLoadSidecarInheritance:
    def test_inherits_resolves_relative_to_current_sidecar(self, tmp_path) -> None:
        base = tmp_path / "base.docx.yaml"
        base.write_text(
            "\n".join(
                [
                    "document:",
                    "  font: { family: Arial, size: 11 }",
                    "defaults:",
                    "  paragraph:",
                    "    spacing: { line: 1.25 }",
                    "blocks:",
                    "  my-table:",
                    "    type: table",
                    "    width: full",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        child = tmp_path / "child.docx.yaml"
        child.write_text(
            "\n".join(
                [
                    "inherits: ./base.docx.yaml",
                    "document:",
                    "  title: Child Document",
                    "defaults:",
                    "  paragraph:",
                    "    spacing: { after: 8 }",
                    "blocks:",
                    "  my-table:",
                    '    background: "EEEEEE"',
                    "",
                ]
            ),
            encoding="utf-8",
        )

        config = load_sidecar(child)

        assert config.document.font.family == "Arial"
        assert config.document.title == "Child Document"
        assert config.defaults["paragraph"].spacing.line == 1.25
        assert config.defaults["paragraph"].spacing.after == 8.0
        assert config.blocks["my-table"].type == "table"
        assert config.blocks["my-table"].style.width == "full"
        assert config.blocks["my-table"].style.background == "EEEEEE"

    def test_missing_inherited_sidecar_raises(self, tmp_path) -> None:
        child = tmp_path / "child.docx.yaml"
        child.write_text("inherits: ./missing.docx.yaml\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Inherited sidecar not found"):
            load_sidecar(child)

    def test_missing_explicit_sidecar_raises(self, tmp_path) -> None:
        missing = tmp_path / "missing.docx.yaml"

        with pytest.raises(FileNotFoundError, match="Sidecar file not found"):
            load_sidecar(missing)

    def test_inheritance_cycle_raises_clear_error(self, tmp_path) -> None:
        a = tmp_path / "a.docx.yaml"
        b = tmp_path / "b.docx.yaml"
        a.write_text("inherits: ./b.docx.yaml\n", encoding="utf-8")
        b.write_text("inherits: ./a.docx.yaml\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Sidecar inheritance cycle detected"):
            load_sidecar(a)
