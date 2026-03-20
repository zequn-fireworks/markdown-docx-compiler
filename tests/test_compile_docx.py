"""End-to-end DOCX compilation checks."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

from markdown_docx_compiler import compile_markdown_file


def test_compile_sample_report_to_docx(tmp_path: Path) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    markdown_path = fixture_dir / "sample_report.md"
    sidecar_path = fixture_dir / "sample_report.docx.yaml"
    output_path = tmp_path / "sample_report.docx"

    result = compile_markdown_file(
        input_path=markdown_path,
        output_path=output_path,
        spec_path=sidecar_path,
    )

    assert result.block_count == 10
    assert output_path.exists()

    with ZipFile(output_path) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
        footer_xml = archive.read("word/footer1.xml").decode("utf-8")
        media_files = {name for name in archive.namelist() if name.startswith("word/media/")}

    assert 'w:tblLayout w:type="fixed"' in document_xml
    assert 'w:tblW w:w="' in document_xml
    assert 'w:type="dxa"' in document_xml
    assert "<w:gridCol" in document_xml
    grid_widths = [int(value) for value in re.findall(r'w:gridCol w:w="(\d+)"', document_xml)]
    assert len(grid_widths) >= 3
    assert grid_widths[0] > grid_widths[1]
    assert "Confidential" in footer_xml
    assert "2026-03-16" in footer_xml
    assert "Draft" in footer_xml
    assert media_files
