"""Manual-review showcase fixtures and regression checks."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

from markdown_docx_compiler import compile_markdown_file
from markdown_docx_compiler.models.document import Heading, Image, List, Table
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_showcase_en_parses_expected_blocks() -> None:
    md_path = FIXTURES / "showcase_en.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    document = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert meta["title"] == "Manual Review Showcase \u2014 English"
    headings = [block for block in document.body if isinstance(block, Heading)]
    tables = [block for block in document.body if isinstance(block, Table)]
    images = [block for block in document.body if isinstance(block, Image)]
    lists = [block for block in document.body if isinstance(block, List)]

    assert len(headings) >= 4
    assert len(tables) == 2
    assert tables[0].meta.anchor == "wide-table"
    assert tables[1].meta.anchor == "compact-table"
    assert len(images) == 1
    assert len(lists) == 1


def test_showcase_zh_parses_expected_blocks() -> None:
    md_path = FIXTURES / "showcase_zh.md"
    meta, body = extract_front_matter(md_path.read_text(encoding="utf-8"))
    document = parse_markdown(body, metadata=meta, md_dir=str(md_path.parent))

    assert "\u4eba\u5de5\u590d\u6838\u793a\u4f8b\u6587\u6863" in meta["title"]
    tables = [block for block in document.body if isinstance(block, Table)]
    assert len(tables) == 1
    assert tables[0].meta.anchor == "zh-results-table"


def test_showcase_en_compiles_with_auto_sidecar_discovery(tmp_path: Path) -> None:
    md_path = FIXTURES / "showcase_en.md"
    output = tmp_path / "showcase_en.docx"

    result = compile_markdown_file(input_path=md_path, output_path=output)

    assert output.exists()
    assert result.spec_path and result.spec_path.endswith("showcase_en.docx.yaml")

    with ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
        footer_xml = archive.read("word/footer1.xml").decode("utf-8")

    grid_widths = [int(value) for value in re.findall(r'w:gridCol w:w="(\d+)"', document_xml)]
    assert len(grid_widths) >= 8
    assert max(grid_widths) > min(grid_widths)
    assert 'w:br w:type="page"' in document_xml
    assert "English Showcase" in footer_xml
    assert "Manual Review" in footer_xml


def test_showcase_zh_compiles_with_expected_footer_and_font_slots(tmp_path: Path) -> None:
    md_path = FIXTURES / "showcase_zh.md"
    output = tmp_path / "showcase_zh.docx"

    result = compile_markdown_file(input_path=md_path, output_path=output)

    assert output.exists()
    assert result.spec_path and result.spec_path.endswith("showcase_zh.docx.yaml")

    with ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
        footer_xml = archive.read("word/footer1.xml").decode("utf-8")

    assert "\u4e2d\u6587\u793a\u4f8b" in footer_xml
    assert "\u4eba\u5de5\u590d\u6838" in footer_xml
    assert 'w:eastAsia="Aptos"' in document_xml
