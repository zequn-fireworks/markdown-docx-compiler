"""End-to-end tests using the real benchmark fixtures."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from markdown_docx_compiler import compile_markdown_file
from markdown_docx_compiler.models.document import (
    Heading,
    Table,
)
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_benchmark_en_parses_all_block_types() -> None:
    md_path = FIXTURES / "benchmark_en.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    doc = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert meta["title"] == "Kimi K2.5 Inference Benchmark — B200 vs B300 (Disaggregated 8+8)"

    block_types = {type(b).__name__ for b in doc.body}
    assert "Heading" in block_types
    assert "Table" in block_types
    assert "HorizontalRule" in block_types
    assert "Image" in block_types
    assert "List" in block_types

    tables = [b for b in doc.body if isinstance(b, Table)]
    assert len(tables) >= 4
    b200_table = tables[2]
    assert b200_table.column_count == 7
    assert b200_table.alignments.count("center") >= 3


def test_benchmark_zh_parses_cjk_content() -> None:
    md_path = FIXTURES / "benchmark_zh.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    doc = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert "\u63a8\u7406\u57fa\u51c6\u6d4b\u8bd5" in meta["title"]

    tables = [b for b in doc.body if isinstance(b, Table)]
    assert len(tables) >= 3

    headings = [b for b in doc.body if isinstance(b, Heading)]
    assert any("\u5ba2\u6237\u76ee\u6807" in h.content[0].text for h in headings if hasattr(h.content[0], "text"))


def test_benchmark_en_compiles_to_docx(tmp_path: Path) -> None:
    md_path = FIXTURES / "benchmark_en.md"
    output = tmp_path / "benchmark_en.docx"

    result = compile_markdown_file(input_path=md_path, output_path=output)

    assert output.exists()
    assert result.block_count > 15

    with ZipFile(output) as archive:
        doc_xml = archive.read("word/document.xml").decode("utf-8")
        media_files = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert "<w:gridCol" in doc_xml
        assert 'w:tblLayout w:type="fixed"' in doc_xml
        assert media_files
        assert doc_xml.count("<w:drawing") >= 4


def test_benchmark_zh_compiles_to_docx(tmp_path: Path) -> None:
    md_path = FIXTURES / "benchmark_zh.md"
    output = tmp_path / "benchmark_zh.docx"

    result = compile_markdown_file(input_path=md_path, output_path=output)

    assert output.exists()
    assert result.block_count > 15

    with ZipFile(output) as archive:
        doc_xml = archive.read("word/document.xml").decode("utf-8")
        media_files = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert "<w:gridCol" in doc_xml
        assert media_files
        assert doc_xml.count("<w:drawing") >= 4
