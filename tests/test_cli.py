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


class TestTopLevel:
    def test_no_args_shows_help(self, _run_cli) -> None:
        completed = _run_cli()
        assert "mdc doc create" in completed.stdout
        assert "document" in completed.stdout
        assert "spec" in completed.stdout
        assert "mdc template" not in completed.stdout
        assert "mdc theme" not in completed.stdout

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
        assert set(data["nouns"]) == {"document", "spec"}

    def test_discovery_nouns_have_verbs(self, _run_cli) -> None:
        completed = _run_cli("--json")
        data = json.loads(completed.stdout)["data"]
        assert "create" in data["nouns"]["document"]["verbs"]
        assert "validate" in data["nouns"]["document"]["verbs"]
        assert "show" in data["nouns"]["spec"]["verbs"]
        assert "template" not in data["nouns"]
        assert "theme" not in data["nouns"]

    def test_discovery_reference_fields(self, _run_cli) -> None:
        completed = _run_cli("--json")
        data = json.loads(completed.stdout)["data"]
        ref = data["reference"]
        assert ref["sidecar_autodiscovery"] == ["<name>.docx.yaml"]
        assert ref["anchor_syntax"] == "<!-- docx:id=name -->"
        assert ref["builtin_document_defaults"]["font"]["family"] == "Aptos"
        assert "paragraph" in ref["block_types"]
        assert "title" in ref["front_matter_keys"]
        assert "font" in ref["block_style_properties"]
        assert len(ref["resolution_order"]) == 4


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

    def test_create_help_documents_default_output_path(self, _run_cli) -> None:
        completed = _run_cli("document", "create", "--help")
        assert "<input>.docx" in completed.stdout


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
        assert payload["data"]["validation_only"] is True
        assert payload["data"]["default_output_path"].endswith("sample_report.docx")


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

    def test_validate_json_includes_inherits_field(self, _run_cli) -> None:
        completed = _run_cli(
            "--json",
            "spec",
            "validate",
            str(FIXTURE_DIR / "sample_report.docx.yaml"),
        )
        payload = json.loads(completed.stdout)
        assert payload["ok"] is True
        assert "inherits" in payload["data"]
        assert payload["data"]["inherits"] is None

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
        assert "inherits:" in completed.stdout
        assert "document:" in completed.stdout
        assert "defaults:" in completed.stdout
        assert "../base.docx.yaml" in completed.stdout

    def test_create_to_file(self, _run_cli, tmp_path) -> None:
        out = tmp_path / "new.docx.yaml"
        completed = _run_cli("spec", "create", str(out))
        assert "Created" in completed.stdout
        assert out.exists()
        content = out.read_text()
        assert "inherits:" in content
        assert "document:" in content


class TestRemovedNouns:
    def test_template_noun_is_unavailable(self, _run_cli) -> None:
        completed = _run_cli("template", "list", check=False)
        assert completed.returncode == 2
        assert "invalid choice" in completed.stderr

    def test_theme_noun_is_unavailable(self, _run_cli) -> None:
        completed = _run_cli("theme", "show", check=False)
        assert completed.returncode == 2
        assert "invalid choice" in completed.stderr


class TestErrorHandling:
    def test_missing_noun_human(self, _run_cli) -> None:
        completed = _run_cli("create", check=False)
        assert completed.returncode == 2
        assert "Missing noun before verb: create" in completed.stderr
        assert "mdc doc create" in completed.stderr

    def test_missing_noun_json(self, _run_cli) -> None:
        completed = _run_cli("--json", "create", check=False)
        assert completed.returncode == 2
        payload = json.loads(completed.stdout)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "MISSING_NOUN"
        assert "mdc doc create" in payload["error"]["hint"]

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

    def test_explicit_spec_not_found_json(self, _run_cli) -> None:
        completed = _run_cli(
            "--json",
            "document",
            "create",
            str(FIXTURE_DIR / "sample_report.md"),
            "--spec",
            "missing.docx.yaml",
            check=False,
        )
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "FILE_NOT_FOUND"

    def test_spec_no_spec_found_json(self, _run_cli, tmp_path) -> None:
        md = tmp_path / "orphan.md"
        md.write_text("# Hello")
        completed = _run_cli("--json", "spec", "show", "--for", str(md), check=False)
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert payload["error"]["code"] == "NO_SPEC_FOUND"


class TestHelpEpilogs:
    def test_document_help_has_markdown_reference(self, _run_cli) -> None:
        completed = _run_cli("document", "--help")
        assert "Supported Markdown" in completed.stdout
        assert "Anchor tags" in completed.stdout
        assert "blocks inside list items" in completed.stdout

    def test_spec_help_has_sidecar_reference(self, _run_cli) -> None:
        completed = _run_cli("spec", "--help")
        assert "Sidecar Config" in completed.stdout

    def test_document_create_help_has_frontmatter(self, _run_cli) -> None:
        completed = _run_cli("document", "create", "--help")
        assert "Front Matter" in completed.stdout

    def test_spec_show_help_has_no_template_flag(self, _run_cli) -> None:
        completed = _run_cli("spec", "show", "--help")
        assert "--template" not in completed.stdout
        assert "matter is included when --for is used" in completed.stdout
