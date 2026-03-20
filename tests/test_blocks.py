"""Tests for block-level parsing into IR."""

from __future__ import annotations

from markdown_docx_compiler.models.document import (
    Blockquote,
    CodeBlock,
    Heading,
    HorizontalRule,
    Image,
    List,
    Paragraph,
    Table,
)
from markdown_docx_compiler.parser import extract_front_matter, parse_markdown


def _parse(md: str):
    meta, body = extract_front_matter(md)
    return parse_markdown(body, metadata=meta)


def test_heading_levels() -> None:
    doc = _parse("# H1\n\n## H2\n\n### H3\n")
    assert len(doc.body) == 3
    assert all(isinstance(b, Heading) for b in doc.body)
    assert [b.level for b in doc.body] == [1, 2, 3]


def test_paragraph() -> None:
    doc = _parse("Hello world.\n")
    assert len(doc.body) == 1
    assert isinstance(doc.body[0], Paragraph)


def test_bullet_list() -> None:
    doc = _parse("- one\n- two\n- three\n")
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, List)
    assert not block.ordered
    assert len(block.items) == 3


def test_ordered_list() -> None:
    doc = _parse("1. first\n2. second\n")
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, List)
    assert block.ordered
    assert len(block.items) == 2


def test_nested_list() -> None:
    md = "- parent\n  - child\n  - child2\n- parent2\n"
    doc = _parse(md)
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, List)
    assert len(block.items) == 2
    nested = [b for b in block.items[0].blocks if isinstance(b, List)]
    assert len(nested) == 1
    assert len(nested[0].items) == 2


def test_table() -> None:
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    doc = _parse(md)
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, Table)
    assert block.column_count == 2
    assert len(block.rows) == 2


def test_table_alignment() -> None:
    md = "| L | C | R |\n|:---|:---:|---:|\n| a | b | c |\n"
    doc = _parse(md)
    block = doc.body[0]
    assert isinstance(block, Table)
    assert block.alignments == ["left", "center", "right"]


def test_code_block() -> None:
    md = "```python\nprint('hello')\n```\n"
    doc = _parse(md)
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, CodeBlock)
    assert block.language == "python"
    assert "print" in block.value


def test_blockquote() -> None:
    doc = _parse("> This is a quote.\n")
    assert len(doc.body) == 1
    assert isinstance(doc.body[0], Blockquote)


def test_horizontal_rule() -> None:
    doc = _parse("text above\n\n---\n\ntext below\n\n---\n")
    hr_blocks = [b for b in doc.body if isinstance(b, HorizontalRule)]
    assert len(hr_blocks) == 2


def test_image() -> None:
    doc = _parse("![alt text](image.png)\n")
    assert len(doc.body) == 1
    block = doc.body[0]
    assert isinstance(block, Image)
    assert block.alt_text == "alt text"
    assert "image.png" in block.path


def test_anchor_captured() -> None:
    md = "<!-- docx:id=my-table -->\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    doc = _parse(md)
    assert len(doc.body) == 1
    assert doc.body[0].meta.anchor == "my-table"


def test_front_matter_metadata() -> None:
    md = "---\ntitle: Test\ndate: 2026-01-01\n---\n\n# Hello\n"
    meta, body = extract_front_matter(md)
    assert meta["title"] == "Test"
    doc = parse_markdown(body, metadata=meta)
    assert doc.metadata["title"] == "Test"
