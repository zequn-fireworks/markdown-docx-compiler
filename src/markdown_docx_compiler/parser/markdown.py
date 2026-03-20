"""Markdown parser front-end producing the new typed document IR.

Parses markdown-it tokens into ``models.document`` types.  Region tags
(``<!-- docx:page_header.left -->``, etc.) are extracted and the tagged
block is routed to the corresponding ``Region`` slot.  Everything else
becomes the body.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdown_docx_compiler.models.document import (
    BlockMeta,
    BlockNode,
    Blockquote,
    CodeBlock,
    CodeSpan,
    Document,
    EmphasisSpan,
    Heading,
    HorizontalRule,
    Image,
    ImageContent,
    InlineNode,
    LineBreak,
    LinkSpan,
    List,
    ListItem,
    Paragraph,
    Region,
    SlotContent,
    StrikeSpan,
    StrongSpan,
    Table,
    TableCell,
    TextContent,
    TextSpan,
    block_type_name,
)

HELP_TOPIC_MARKDOWN = """\
# Supported Markdown

## Block features

- headings (h1-h6)
- paragraphs
- ordered and bullet lists, including nesting
- fenced code blocks
- blockquotes
- horizontal rules
- tables (pipe syntax)
- standalone images via ![alt](path)

## Inline features

- **bold**
- *italic*
- ~~strikethrough~~
- `inline code`
- [links](url)
- hard and soft line breaks

## Region tags

Place content into page headers, footers, or a doc header:

  <!-- docx:page_header.left -->
  <!-- docx:page_footer.right -->
  <!-- docx:doc_header.left -->

The next top-level paragraph, heading, or standalone image is extracted into
the region slot. Other block types are rejected.

## Anchor tags

Tag a block for instance-level styling:

  <!-- docx:id=results-table -->

Reference the anchor in the sidecar `blocks:` section.
Anchors apply to the next body block, including blocks inside list items.
Region tags remain top-level-only.

## Not supported

These features are not handled by the compiler:

- arbitrary HTML (except `docx:` tags)
- footnotes
- task lists (checkboxes)
- math / LaTeX
- custom inline directives
- definition lists
- nested block structures inside blockquotes

The only recognized HTML is `docx:` tags written with HTML comment syntax
(see `mdc doc --help`):

  <!-- docx:id=name -->
  <!-- docx:page_footer.right -->
"""

HELP_TOPIC_ANCHORS = """\
# Anchors

Anchors are optional `docx:` tags that mark specific blocks for styling
from the sidecar config.

## Syntax

  <!-- docx:id=name -->

## Rules

- The tag must be on its own line.
- It applies to the next body block.
- The tag itself is not rendered in the output.
- Only `docx:` tags are treated as compiler metadata.
- Anchor tags can target blocks inside list items.
- Region tags remain top-level-only.

## Example

Markdown:

  <!-- docx:id=results-table -->
  | Model | TTFT | TPS |
  | --- | ---: | ---: |
  | A | 120 | 80 |

Sidecar:

  blocks:
    results-table:
      type: table
      table: { columns: [3fr, 1fr, 1fr] }

## When to use anchors

Use anchors when you need to target one specific block that type defaults
cannot distinguish.
"""

_ANCHOR_RE = re.compile(r"<!--\s*docx:(.*?)-->")
_KV_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)=("[^"]*"|[^"\s]+)')
_REGION_RE = re.compile(r"(page_header|page_footer|doc_header)\.(left|center|right)")

_REGION_NAMES = frozenset({"page_header", "page_footer", "doc_header"})
_SLOT_NAMES = frozenset({"left", "center", "right"})


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_markdown(
    markdown_text: str,
    *,
    metadata: dict[str, Any],
    md_dir: str = ".",
) -> Document:
    """Parse markdown text into a ``Document``."""
    md = MarkdownIt("commonmark", {"typographer": True}).enable(["table", "strikethrough"])
    tokens = md.parse(markdown_text)
    walker = _IRWalker(md_dir=md_dir)
    return walker.build(tokens, metadata=metadata)


# ---------------------------------------------------------------------------
# Walker
# ---------------------------------------------------------------------------


class _IRWalker:
    def __init__(self, *, md_dir: str) -> None:
        self.md_dir = md_dir
        self._pending_anchor: str | None = None
        self._pending_region: tuple[str, str] | None = None  # (region, slot)
        self._block_index = 0

    def build(self, tokens: list[Token], *, metadata: dict[str, Any]) -> Document:
        raw_blocks = self._walk(tokens)

        body: list[BlockNode] = []
        regions: dict[str, dict[str, list[SlotContent]]] = {
            "page_header": {"left": [], "center": [], "right": []},
            "page_footer": {"left": [], "center": [], "right": []},
            "doc_header": {"left": [], "center": [], "right": []},
        }

        for region_tag, block in raw_blocks:
            if region_tag is not None:
                region_name, slot_name = region_tag
                if isinstance(block, Image):
                    regions[region_name][slot_name].append(ImageContent(path=block.path, alt_text=block.alt_text))
                elif isinstance(block, (Paragraph, Heading)):
                    regions[region_name][slot_name].append(TextContent(content=block.content))
                else:
                    raise ValueError(
                        "Region tags only support top-level paragraphs, headings, and standalone images; "
                        f"`docx:{region_name}.{slot_name}` targeted a {block_type_name(block)} block."
                    )
            else:
                body.append(block)

        return Document(
            metadata=metadata,
            page_header=Region(**regions["page_header"]),
            page_footer=Region(**regions["page_footer"]),
            doc_header=Region(**regions["doc_header"]),
            body=body,
        )

    def _walk(self, tokens: list[Token]) -> list[tuple[tuple[str, str] | None, BlockNode]]:
        results: list[tuple[tuple[str, str] | None, BlockNode]] = []
        index = 0
        while index < len(tokens):
            token = tokens[index]

            if self._capture_docx_tag(token):
                index += 1
                continue

            region_tag = self._pending_region
            self._pending_region = None

            if token.type == "heading_open":
                level = int(token.tag[1])
                inline = tokens[index + 1]
                content = _inline_from_token(inline)
                results.append((region_tag, Heading(level=level, content=content, meta=self._next_meta())))
                index += 3
                continue

            if token.type == "paragraph_open":
                inline = tokens[index + 1]
                image = _image_from_inline(inline)
                if image is not None:
                    path, alt, title = image
                    results.append(
                        (
                            region_tag,
                            Image(
                                path=self._resolve_path(path),
                                alt_text=alt,
                                title=title,
                                meta=self._next_meta(),
                            ),
                        )
                    )
                else:
                    results.append(
                        (
                            region_tag,
                            Paragraph(content=_inline_from_token(inline), meta=self._next_meta()),
                        )
                    )
                index += 3
                continue

            if token.type in {"bullet_list_open", "ordered_list_open"}:
                ordered = token.type == "ordered_list_open"
                close_type = "ordered_list_close" if ordered else "bullet_list_close"
                list_anchor = self._take_pending_anchor()
                list_block, end_index = self._collect_list(tokens=tokens, start=index + 1, close_type=close_type)
                list_block = replace(list_block, meta=self._meta_from_anchor(list_anchor))
                results.append((region_tag, list_block))
                index = end_index + 1
                continue

            if token.type == "table_open":
                table_block, end_index = self._collect_table(tokens=tokens, start=index + 1)
                results.append((region_tag, replace(table_block, meta=self._next_meta())))
                index = end_index + 1
                continue

            if token.type == "fence":
                results.append(
                    (
                        region_tag,
                        CodeBlock(
                            value=token.content.rstrip("\n"),
                            language=token.info.strip() or None,
                            meta=self._next_meta(),
                        ),
                    )
                )
                index += 1
                continue

            if token.type == "blockquote_open":
                quote, end_index = self._collect_blockquote(tokens=tokens, start=index + 1)
                results.append((region_tag, Blockquote(content=quote, meta=self._next_meta())))
                index = end_index + 1
                continue

            if token.type == "hr":
                results.append((region_tag, HorizontalRule(meta=self._next_meta())))
                index += 1
                continue

            index += 1

        return results

    # -- docx tag capture --------------------------------------------------

    def _parse_docx_tag(self, token: Token) -> tuple[str, str | tuple[str, str]] | None:
        content = (token.content or "").strip()
        if token.type not in {"html_block", "html_inline"}:
            return None
        match = _ANCHOR_RE.fullmatch(content)
        if not match:
            return None
        payload = match.group(1).strip()

        region_match = _REGION_RE.fullmatch(payload)
        if region_match:
            return "region", (region_match.group(1), region_match.group(2))

        kv = _parse_kv_payload(payload)
        anchor_id = kv.get("id")
        if anchor_id:
            return "anchor", anchor_id

        return None

    def _capture_docx_tag(self, token: Token) -> bool:
        parsed = self._parse_docx_tag(token)
        if parsed is None:
            return False
        kind, payload = parsed
        if kind == "region":
            assert isinstance(payload, tuple)
            region_name, slot_name = payload
            self._pending_region = (region_name, slot_name)
            self._pending_anchor = None
            return True

        self._pending_anchor = str(payload)
        self._pending_region = None
        return True

    def _reject_nested_docx_tag(self, token: Token, *, container: str, allow_anchor: bool = False) -> None:
        parsed = self._parse_docx_tag(token)
        if parsed is None:
            return
        kind, _payload = parsed
        if kind == "anchor":
            if allow_anchor:
                return
            raise ValueError(f"Anchor tags are not supported inside {container}.")
        raise ValueError(
            "Region tags are only supported on top-level paragraphs, headings, and standalone images, "
            f"not inside {container}."
        )

    # -- Metadata helpers --------------------------------------------------

    def _next_index(self) -> int:
        self._block_index += 1
        return self._block_index

    def _take_pending_anchor(self) -> str | None:
        anchor = self._pending_anchor
        self._pending_anchor = None
        return anchor

    def _meta_from_anchor(self, anchor: str | None) -> BlockMeta:
        return BlockMeta(anchor=anchor, index=self._next_index())

    def _next_meta(self) -> BlockMeta:
        return self._meta_from_anchor(self._take_pending_anchor())

    def _resolve_path(self, path: str) -> str:
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str((Path(self.md_dir) / p).resolve())

    # -- Block collectors --------------------------------------------------

    def _collect_list(self, *, tokens: list[Token], start: int, close_type: str) -> tuple[List, int]:
        items: list[ListItem] = []
        ordered = close_type == "ordered_list_close"
        index = start

        while index < len(tokens):
            token = tokens[index]
            if token.type == close_type:
                return List(ordered=ordered, items=items), index
            if token.type != "list_item_open":
                index += 1
                continue

            item_blocks: list[BlockNode] = []
            index += 1
            while index < len(tokens) and tokens[index].type != "list_item_close":
                token = tokens[index]
                self._reject_nested_docx_tag(token, container="list items", allow_anchor=True)
                if self._capture_docx_tag(token):
                    index += 1
                    continue
                if token.type == "heading_open":
                    level = int(token.tag[1])
                    inline = tokens[index + 1]
                    item_blocks.append(Heading(level=level, content=_inline_from_token(inline), meta=self._next_meta()))
                    index += 3
                    continue
                if token.type == "paragraph_open":
                    inline = tokens[index + 1]
                    image = _image_from_inline(inline)
                    if image is not None:
                        path, alt, title = image
                        item_blocks.append(
                            Image(
                                path=self._resolve_path(path),
                                alt_text=alt,
                                title=title,
                                meta=self._next_meta(),
                            )
                        )
                    else:
                        item_blocks.append(Paragraph(content=_inline_from_token(inline), meta=self._next_meta()))
                    index += 3
                    continue
                if token.type in {"bullet_list_open", "ordered_list_open"}:
                    nested_ordered = token.type == "ordered_list_open"
                    nested_close = "ordered_list_close" if nested_ordered else "bullet_list_close"
                    nested_anchor = self._take_pending_anchor()
                    nested_list, index = self._collect_list(tokens=tokens, start=index + 1, close_type=nested_close)
                    item_blocks.append(replace(nested_list, meta=self._meta_from_anchor(nested_anchor)))
                    index += 1
                    continue
                if token.type == "table_open":
                    table_block, end_index = self._collect_table(tokens=tokens, start=index + 1)
                    item_blocks.append(replace(table_block, meta=self._next_meta()))
                    index = end_index + 1
                    continue
                if token.type == "fence":
                    item_blocks.append(
                        CodeBlock(
                            value=token.content.rstrip("\n"),
                            language=token.info.strip() or None,
                            meta=self._next_meta(),
                        )
                    )
                    index += 1
                    continue
                if token.type == "blockquote_open":
                    quote, end_index = self._collect_blockquote(tokens=tokens, start=index + 1)
                    item_blocks.append(Blockquote(content=quote, meta=self._next_meta()))
                    index = end_index + 1
                    continue
                if token.type == "hr":
                    item_blocks.append(HorizontalRule(meta=self._next_meta()))
                    index += 1
                    continue
                index += 1
            items.append(ListItem(blocks=item_blocks))
            index += 1

        return List(ordered=ordered, items=items), index

    def _collect_table(self, *, tokens: list[Token], start: int) -> tuple[Table, int]:
        headers: list[TableCell] = []
        rows: list[list[TableCell]] = []
        alignments: list[Literal["left", "center", "right"]] = []
        current_row: list[TableCell] = []
        in_head = False
        in_body = False
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.type == "table_close":
                return Table(headers=headers, rows=rows, alignments=alignments), index
            if token.type == "thead_open":
                in_head = True
            elif token.type == "thead_close":
                in_head = False
            elif token.type == "tbody_open":
                in_body = True
            elif token.type == "tbody_close":
                in_body = False
            elif token.type == "tr_open":
                current_row = []
            elif token.type == "tr_close":
                if in_head:
                    headers = current_row
                elif in_body:
                    rows.append(current_row)
            elif token.type in {"th_open", "td_open"}:
                if token.type == "th_open":
                    alignments.append(_alignment_from_attrs(token.attrs))
                inline = tokens[index + 1]
                current_row.append(TableCell(content=_inline_from_token(inline)))
                index += 2
            index += 1
        return Table(headers=headers, rows=rows, alignments=alignments), index

    def _collect_blockquote(self, *, tokens: list[Token], start: int) -> tuple[list[InlineNode], int]:
        parts: list[InlineNode] = []
        index = start
        while index < len(tokens):
            token = tokens[index]
            if token.type == "blockquote_close":
                return parts, index
            self._reject_nested_docx_tag(token, container="blockquotes")
            if token.type == "paragraph_close":
                next_token = tokens[index + 1] if index + 1 < len(tokens) else None
                if next_token is not None and next_token.type != "blockquote_close":
                    parts.append(LineBreak(hard=True))
                index += 1
                continue
            if token.type in {"paragraph_open"}:
                index += 1
                continue
            if token.type not in {"inline"}:
                raise ValueError(
                    "Blockquotes currently support paragraph content only; nested lists, tables, code blocks, "
                    "and other block structures inside blockquotes are not supported."
                )
            if token.type == "inline":
                parts.extend(_inline_from_token(token))
            index += 1
        return parts, index


# ---------------------------------------------------------------------------
# Inline parsing
# ---------------------------------------------------------------------------


def _inline_from_token(token: Token) -> list[InlineNode]:
    children = token.children or []
    parsed, _ = _inline_from_children(children=children, start=0, end_types=set())
    return parsed


def _inline_from_children(*, children: list[Token], start: int, end_types: set[str]) -> tuple[list[InlineNode], int]:
    items: list[InlineNode] = []
    index = start
    while index < len(children):
        child = children[index]
        if child.type in end_types:
            return items, index
        if child.type == "text":
            items.append(TextSpan(child.content))
        elif child.type == "softbreak":
            items.append(LineBreak(hard=False))
        elif child.type == "hardbreak":
            items.append(LineBreak(hard=True))
        elif child.type == "code_inline":
            items.append(CodeSpan(child.content))
        elif child.type == "strong_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"strong_close"})
            items.append(StrongSpan(nested))
        elif child.type == "em_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"em_close"})
            items.append(EmphasisSpan(nested))
        elif child.type == "s_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"s_close"})
            items.append(StrikeSpan(nested))
        elif child.type == "link_open":
            nested, index = _inline_from_children(children=children, start=index + 1, end_types={"link_close"})
            href = ""
            if child.attrs:
                href = str(child.attrs.get("href", ""))
            items.append(LinkSpan(url=href, children=nested))
        index += 1
    return items, index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _image_from_inline(token: Token) -> tuple[str, str, str | None] | None:
    children = token.children or []
    non_empty = [
        child
        for child in children
        if child.type != "softbreak" and not (child.type == "text" and not child.content.strip())
    ]
    if len(non_empty) != 1 or non_empty[0].type != "image":
        return None
    image = non_empty[0]
    src = str(image.attrs.get("src", "")) if image.attrs else ""
    title_raw = image.attrs.get("title") if image.attrs else None
    title = str(title_raw) if title_raw is not None else None
    return src, image.content or "", title


def _alignment_from_attrs(attrs: dict[str, str | int | float] | None) -> Literal["left", "center", "right"]:
    style = str(attrs.get("style", "")) if attrs else ""
    if "right" in style:
        return "right"
    if "center" in style:
        return "center"
    return "left"


def _parse_kv_payload(payload: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for key, raw_value in _KV_RE.findall(payload):
        data[key] = raw_value.strip('"')
    return data
