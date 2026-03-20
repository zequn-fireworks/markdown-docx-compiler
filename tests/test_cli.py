"""CLI smoke tests for the noun-verb interface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def _run_cli():
    """Helper to run the CLI as a subprocess."""

    def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "markdown_docx_compiler", *args],
            capture_output=True,
            text=True,
            check=check,
        )

    return _run


# ---------------------------------------------------------------------------
# Top-level and discovery
# ---------------------------------------------------------------------------


class TestTopLevel:
    def test_no_args_shows_help(self, _run_cli) -> None:
        completed = _run_cli()
        assert "mdc doc create" in completed.stdout
        assert "--template" not in completed.stdout
        assert "document" in completed.stdout
        assert "spec" in completed.stdout

    def test_version(self, _run_cli) -> None:
        completed = _run_cli("--version")
        assert "mdc" in completed.stdout

    def test_json_discovery_payload(self, _run_cli) -> None:
        completed = _run_cli("--json")
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert payload["command"] == "discovery"
        data = payload["data"]
        assert "version" in data
        assert "document" in data["nouns"]
        assert "spec" in data["nouns"]
        assert "template" in data["nouns"]
        assert "theme" in data["nouns"]

    def test_discovery_nouns_have_verbs(self, _run_cli) -> None:
        completed = _run_cli("--json")
        data = json.loads(completed.stdout)["data"]
        assert "create" in data["nouns"]["document"]["verbs"]
        assert "validate" in data["nouns"]["document"]["verbs"]
        assert "show" in data["nouns"]["spec"]["verbs"]
        assert "list" in data["nouns"]["template"]["verbs"]

    def test_discovery_reference_fields(self, _run_cli) -> None:
        completed = _run_cli("--json")
        data = json.loads(completed.stdout)["data"]
        ref = data["reference"]
        assert "<name>.docx.yaml" in ref["sidecar_autodiscovery"]
        assert ref["anchor_syntax"] == "<!-- docx:id=name -->"
        assert "font" in ref["default_brand"]
        assert "paragraph" in ref["block_types"]
        assert "title" in ref["front_matter_keys"]
        assert "font" in ref["block_style_properties"]
        assert len(ref["resolution_order"]) == 4


# ---------------------------------------------------------------------------
# Document noun
# ---------------------------------------------------------------------------


class TestDocumentCreate:
    def test_create_writes_docx(self, _run_cli, tmp_path) -> None:
        out = tmp_path / "out.docx"
        completed = _run_cli(
            "document",
            "create",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
            "-o",
            str(out),
        )
        assert "Wrote" in completed.stdout
        assert out.exists()

    def test_create_json_output(self, _run_cli, tmp_path) -> None:
        out = tmp_path / "out.docx"
        completed = _run_cli(
            "--json",
            "document",
            "create",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
            "-o",
            str(out),
        )
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert payload["command"] == "document create"

    def test_abbreviation_doc(self, _run_cli, tmp_path) -> None:
        out = tmp_path / "out.docx"
        completed = _run_cli(
            "doc",
            "create",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
            "-o",
            str(out),
        )
        assert "Wrote" in completed.stdout


class TestDocumentValidate:
    def test_validate_reports_blocks(self, _run_cli) -> None:
        completed = _run_cli(
            "document",
            "validate",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
        )
        assert "Valid" in completed.stdout
        assert "blocks" in completed.stdout

    def test_validate_json(self, _run_cli) -> None:
        completed = _run_cli(
            "--json",
            "document",
            "validate",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
        )
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert payload["data"]["dry_run"] is True


# ---------------------------------------------------------------------------
# Spec noun
# ---------------------------------------------------------------------------


class TestSpecShow:
    def test_show_direct_path(self, _run_cli) -> None:
        completed = _run_cli(
            "spec",
            "show",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
        )
        assert "sample_report.docx.yaml" in completed.stdout

    def test_show_for_document(self, _run_cli) -> None:
        completed = _run_cli(
            "spec",
            "show",
            "--for",
            str(FIXTURE_DIR / "sample_report.md"),
        )
        assert "sample_report.docx.yaml" in completed.stdout

    def test_show_resolved_json(self, _run_cli) -> None:
        completed = _run_cli(
            "--json",
            "spec",
            "show",
            "--for",
            str(FIXTURE_DIR / "sample_report.md"),
            "--resolved",
        )
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert "document_config" in payload["data"]
        assert "resolved_sidecar" in payload["data"]


class TestSpecValidate:
    def test_validate_sidecar(self, _run_cli) -> None:
        completed = _run_cli(
            "spec",
            "validate",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
        )
        assert "Valid" in completed.stdout

    def test_validate_for_document(self, _run_cli) -> None:
        completed = _run_cli(
            "spec",
            "validate",
            "--for",
            str(FIXTURE_DIR / "sample_report.md"),
        )
        assert "Valid" in completed.stdout


class TestSpecCreate:
    def test_create_to_stdout(self, _run_cli) -> None:
        completed = _run_cli("spec", "create")
        assert "document:" in completed.stdout
        assert "defaults:" in completed.stdout

    def test_create_to_file(self, _run_cli, tmp_path) -> None:
        out = tmp_path / "new.docx.yaml"
        completed = _run_cli("spec", "create", str(out))
        assert "Created" in completed.stdout
        assert out.exists()
        content = out.read_text()
        assert "document:" in content


# ---------------------------------------------------------------------------
# Template noun
# ---------------------------------------------------------------------------


class TestTemplateList:
    def test_list_shows_default(self, _run_cli) -> None:
        completed = _run_cli("template", "list")
        assert "default" in completed.stdout

    def test_list_json(self, _run_cli) -> None:
        completed = _run_cli("--json", "template", "list")
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        names = [t["name"] for t in payload["data"]["templates"]]
        assert "default" in names

    def test_abbreviation_tpl(self, _run_cli) -> None:
        completed = _run_cli("tpl", "list")
        assert "default" in completed.stdout


class TestTemplateShow:
    def test_show_default(self, _run_cli) -> None:
        completed = _run_cli("template", "show", "default")
        assert "default" in completed.stdout

    def test_show_unknown_errors(self, _run_cli) -> None:
        completed = _run_cli("--json", "template", "show", "nonexistent", check=False)
        assert completed.returncode != 0
        payload = json.loads(completed.stdout)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "UNKNOWN_TEMPLATE"


# ---------------------------------------------------------------------------
# Theme noun
# ---------------------------------------------------------------------------


class TestThemeList:
    def test_list_shows_default(self, _run_cli) -> None:
        completed = _run_cli("theme", "list")
        assert "default" in completed.stdout

    def test_list_json(self, _run_cli) -> None:
        completed = _run_cli("--json", "theme", "list")
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        names = [t["name"] for t in payload["data"]["themes"]]
        assert "default" in names


class TestThemeShow:
    def test_show_default(self, _run_cli) -> None:
        completed = _run_cli("theme", "show")
        assert "default" in completed.stdout
        assert "font:" in completed.stdout

    def test_show_json(self, _run_cli) -> None:
        completed = _run_cli("--json", "theme", "show", "default")
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert payload["data"]["name"] == "default"
        assert "variants" in payload["data"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_file_not_found_human(self, _run_cli) -> None:
        completed = _run_cli("document", "create", "nonexistent.md", check=False)
        assert completed.returncode == 1
        assert "Error:" in completed.stderr
        assert "Hint:" in completed.stderr

    def test_file_not_found_json(self, _run_cli) -> None:
        completed = _run_cli("--json", "document", "create", "nonexistent.md", check=False)
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "FILE_NOT_FOUND"
        assert "hint" in payload["error"]

    def test_spec_no_spec_found_json(self, _run_cli, tmp_path) -> None:
        md = tmp_path / "orphan.md"
        md.write_text("# Hello")
        completed = _run_cli("--json", "spec", "show", "--for", str(md), check=False)
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert payload["error"]["code"] == "NO_SPEC_FOUND"


# ---------------------------------------------------------------------------
# Help integration
# ---------------------------------------------------------------------------


class TestHelpEpilogs:
    def test_document_help_has_markdown_reference(self, _run_cli) -> None:
        completed = _run_cli("document", "--help")
        assert "Supported Markdown" in completed.stdout
        assert "Anchor tags" in completed.stdout

    def test_spec_help_has_sidecar_reference(self, _run_cli) -> None:
        completed = _run_cli("spec", "--help")
        assert "Sidecar Config" in completed.stdout

    def test_document_create_help_has_frontmatter(self, _run_cli) -> None:
        completed = _run_cli("document", "create", "--help")
        assert "Front Matter" in completed.stdout

    def test_template_help_avoids_nonexistent_template_flag(self, _run_cli) -> None:
        completed = _run_cli("template", "--help")
        assert "--template" not in completed.stdout
        assert "mdc template list" in completed.stdout
