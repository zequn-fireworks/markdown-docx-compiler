"""Tests for compiler.py — sidecar discovery, path resolution, and error paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from markdown_docx_compiler.compiler import CompileResult, compile_markdown_file, discover_sidecar_path


class TestDiscoverSidecarPath:
    def test_finds_docx_yaml(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        sidecar = tmp_path / "report.docx.yaml"
        sidecar.write_text("document:\n  theme: default\n")
        assert discover_sidecar_path(md) == sidecar

    def test_finds_docx_yml(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        sidecar = tmp_path / "report.docx.yml"
        sidecar.write_text("document:\n  theme: default\n")
        assert discover_sidecar_path(md) == sidecar

    def test_finds_docspec_yaml(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        sidecar = tmp_path / "report.docspec.yaml"
        sidecar.write_text("document:\n  theme: default\n")
        assert discover_sidecar_path(md) == sidecar

    def test_finds_docspec_yml(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        sidecar = tmp_path / "report.docspec.yml"
        sidecar.write_text("document:\n  theme: default\n")
        assert discover_sidecar_path(md) == sidecar

    def test_returns_none_when_no_sidecar(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        assert discover_sidecar_path(md) is None

    def test_prefers_first_candidate(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Hello")
        yaml_path = tmp_path / "report.docx.yaml"
        yml_path = tmp_path / "report.docx.yml"
        yaml_path.write_text("document:\n  theme: default\n")
        yml_path.write_text("document:\n  theme: fireworks\n")
        assert discover_sidecar_path(md) == yaml_path


class TestCompileMarkdownFile:
    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            compile_markdown_file(input_path=tmp_path / "missing.md")

    def test_dry_run_produces_result_without_docx(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Test\n\nHello world.\n")
        result = compile_markdown_file(input_path=md, dry_run=True)
        assert isinstance(result, CompileResult)
        assert result.dry_run is True
        assert result.block_count >= 1
        docx_path = Path(result.output_path)
        assert not docx_path.exists()

    def test_default_output_path(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Test\n\nHello.\n")
        result = compile_markdown_file(input_path=md, dry_run=True)
        assert result.output_path.endswith(".docx")
        assert "report.docx" in result.output_path

    def test_compile_produces_docx(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Title\n\nBody paragraph.\n")
        out = tmp_path / "out.docx"
        result = compile_markdown_file(input_path=md, output_path=out)
        assert result.dry_run is False
        assert out.exists()
        assert out.stat().st_size > 0

    def test_compile_with_explicit_spec(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("---\ntitle: Test\n---\n# Title\n\nBody.\n")
        spec = tmp_path / "spec.yaml"
        spec.write_text("template: fireworks\n")
        out = tmp_path / "out.docx"
        result = compile_markdown_file(input_path=md, output_path=out, spec_path=spec)
        assert result.theme == "fireworks"
        assert result.spec_path is not None

    def test_compile_auto_discovers_sidecar(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Title\n\nBody.\n")
        sidecar = tmp_path / "report.docx.yaml"
        sidecar.write_text("template: fireworks\n")
        out = tmp_path / "out.docx"
        result = compile_markdown_file(input_path=md, output_path=out)
        assert result.theme == "fireworks"

    def test_to_dict(self, tmp_path: Path) -> None:
        md = tmp_path / "report.md"
        md.write_text("# Test\n")
        result = compile_markdown_file(input_path=md, dry_run=True)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "input_path" in d
        assert "block_count" in d
        assert "dry_run" in d
