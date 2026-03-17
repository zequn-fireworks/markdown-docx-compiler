"""Tests for inline token walking into IR nodes."""

from __future__ import annotations

from markdown_it import MarkdownIt

from markdown_docx_compiler.ir import CodeSpan, Emphasis, Link, Strike, Strong, Text
from markdown_docx_compiler.parser.markdown_parser import _inline_from_token


def _parse_inline(md_text: str):
    """Parse a single paragraph's inline content into IR nodes."""
    md = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "strikethrough"])
    tokens = md.parse(md_text)
    for token in tokens:
        if token.type == "inline":
            return _inline_from_token(token)
    return []


def _significant(nodes):
    """Filter out empty Text nodes that markdown-it produces around formatting."""
    return [n for n in nodes if not (isinstance(n, Text) and n.value == "")]


def test_plain_text() -> None:
    nodes = _parse_inline("hello world")
    assert len(nodes) == 1
    assert isinstance(nodes[0], Text)
    assert nodes[0].value == "hello world"


def test_bold() -> None:
    nodes = _significant(_parse_inline("**bold text**"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], Strong)
    assert isinstance(nodes[0].children[0], Text)
    assert nodes[0].children[0].value == "bold text"


def test_italic() -> None:
    nodes = _significant(_parse_inline("*italic*"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], Emphasis)


def test_bold_italic() -> None:
    nodes = _significant(_parse_inline("***bold italic***"))
    assert len(nodes) == 1
    outer = nodes[0]
    assert isinstance(outer, Strong | Emphasis)
    inner_content = _significant(outer.children)
    assert len(inner_content) == 1
    inner = inner_content[0]
    assert isinstance(inner, Strong | Emphasis)
    assert {type(outer), type(inner)} == {Strong, Emphasis}
    leaf = _significant(inner.children)
    assert leaf[0].value == "bold italic"


def test_strikethrough() -> None:
    nodes = _significant(_parse_inline("~~deleted~~"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], Strike)
    assert nodes[0].children[0].value == "deleted"


def test_inline_code() -> None:
    nodes = _parse_inline("`code`")
    assert len(nodes) == 1
    assert isinstance(nodes[0], CodeSpan)
    assert nodes[0].value == "code"


def test_double_backtick_code_span() -> None:
    nodes = _parse_inline("``a`b``")
    assert len(nodes) == 1
    assert isinstance(nodes[0], CodeSpan)
    assert nodes[0].value == "a`b"


def test_link() -> None:
    nodes = _parse_inline("[click here](https://example.com)")
    assert len(nodes) == 1
    assert isinstance(nodes[0], Link)
    assert nodes[0].url == "https://example.com"
    assert nodes[0].children[0].value == "click here"


def test_mixed_inline() -> None:
    nodes = _parse_inline("Hello **bold** and *italic* and `code`")
    texts = []
    for node in nodes:
        if isinstance(node, Text):
            texts.append(("text", node.value))
        elif isinstance(node, Strong):
            texts.append(("strong", node.children[0].value))
        elif isinstance(node, Emphasis):
            texts.append(("em", node.children[0].value))
        elif isinstance(node, CodeSpan):
            texts.append(("code", node.value))
    assert ("text", "Hello ") in texts
    assert ("strong", "bold") in texts
    assert ("em", "italic") in texts
    assert ("code", "code") in texts


def test_bold_text_ending_with_backslash() -> None:
    nodes = _significant(_parse_inline("**text\\\\**"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], Strong)
    assert nodes[0].children[0].value == "text\\"
