"""Tests for inline token walking into IR nodes."""

from __future__ import annotations

from markdown_it import MarkdownIt

from markdown_docx_compiler.models.document import (
    CodeSpan,
    EmphasisSpan,
    LinkSpan,
    StrikeSpan,
    StrongSpan,
    TextSpan,
)
from markdown_docx_compiler.parser.markdown import _inline_from_token


def _parse_inline(md_text: str):
    """Parse a single paragraph's inline content into IR nodes."""
    md = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "strikethrough"])
    tokens = md.parse(md_text)
    for token in tokens:
        if token.type == "inline":
            return _inline_from_token(token)
    return []


def _significant(nodes):
    """Filter out empty TextSpan nodes that markdown-it produces around formatting."""
    return [n for n in nodes if not (isinstance(n, TextSpan) and n.text == "")]


def test_plain_text() -> None:
    nodes = _parse_inline("hello world")
    assert len(nodes) == 1
    assert isinstance(nodes[0], TextSpan)
    assert nodes[0].text == "hello world"


def test_bold() -> None:
    nodes = _significant(_parse_inline("**bold text**"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], StrongSpan)
    assert isinstance(nodes[0].children[0], TextSpan)
    assert nodes[0].children[0].text == "bold text"


def test_italic() -> None:
    nodes = _significant(_parse_inline("*italic*"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], EmphasisSpan)


def test_bold_italic() -> None:
    nodes = _significant(_parse_inline("***bold italic***"))
    assert len(nodes) == 1
    outer = nodes[0]
    assert isinstance(outer, StrongSpan | EmphasisSpan)
    inner_content = _significant(outer.children)
    assert len(inner_content) == 1
    inner = inner_content[0]
    assert isinstance(inner, StrongSpan | EmphasisSpan)
    assert {type(outer), type(inner)} == {StrongSpan, EmphasisSpan}
    leaf = _significant(inner.children)
    assert leaf[0].text == "bold italic"


def test_strikethrough() -> None:
    nodes = _significant(_parse_inline("~~deleted~~"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], StrikeSpan)
    assert nodes[0].children[0].text == "deleted"


def test_inline_code() -> None:
    nodes = _parse_inline("`code`")
    assert len(nodes) == 1
    assert isinstance(nodes[0], CodeSpan)
    assert nodes[0].text == "code"


def test_double_backtick_code_span() -> None:
    nodes = _parse_inline("``a`b``")
    assert len(nodes) == 1
    assert isinstance(nodes[0], CodeSpan)
    assert nodes[0].text == "a`b"


def test_link() -> None:
    nodes = _parse_inline("[click here](https://example.com)")
    assert len(nodes) == 1
    assert isinstance(nodes[0], LinkSpan)
    assert nodes[0].url == "https://example.com"
    assert nodes[0].children[0].text == "click here"


def test_mixed_inline() -> None:
    nodes = _parse_inline("Hello **bold** and *italic* and `code`")
    texts = []
    for node in nodes:
        if isinstance(node, TextSpan):
            texts.append(("text", node.text))
        elif isinstance(node, StrongSpan):
            texts.append(("strong", node.children[0].text))
        elif isinstance(node, EmphasisSpan):
            texts.append(("em", node.children[0].text))
        elif isinstance(node, CodeSpan):
            texts.append(("code", node.text))
    assert ("text", "Hello ") in texts
    assert ("strong", "bold") in texts
    assert ("em", "italic") in texts
    assert ("code", "code") in texts


def test_bold_text_ending_with_backslash() -> None:
    nodes = _significant(_parse_inline("**text\\\\**"))
    assert len(nodes) == 1
    assert isinstance(nodes[0], StrongSpan)
    assert nodes[0].children[0].text == "text\\"
