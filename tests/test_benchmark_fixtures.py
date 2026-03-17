"""End-to-end tests using the real benchmark fixtures from the Fireworks repo."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from markdown_docx_compiler import compile_markdown_file
from markdown_docx_compiler.ir import (
    HeadingBlock,
    TableBlock,
)
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_benchmark_en_parses_all_block_types() -> None:
    md_path = FIXTURES / "benchmark_en.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    doc = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert meta["title"] == "Kimi K2.5 Inference Benchmark — B200 vs B300 (Disaggregated 8+8)"

    block_types = {type(b).__name__ for b in doc.blocks}
    assert "HeadingBlock" in block_types
    assert "TableBlock" in block_types
    assert "HorizontalRuleBlock" in block_types
    assert "ImageBlock" in block_types
    assert "ListBlock" in block_types

    tables = [b for b in doc.blocks if isinstance(b, TableBlock)]
    assert len(tables) >= 4
    b200_table = tables[2]
    assert b200_table.column_count == 7
    assert b200_table.alignments.count("center") >= 3


def test_benchmark_zh_parses_cjk_content() -> None:
    md_path = FIXTURES / "benchmark_zh.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    doc = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert "推理基准测试" in meta["title"]

    tables = [b for b in doc.blocks if isinstance(b, TableBlock)]
    assert len(tables) >= 3

    headings = [b for b in doc.blocks if isinstance(b, HeadingBlock)]
    assert any("客户目标" in h.content[0].value for h in headings if hasattr(h.content[0], "value"))


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
