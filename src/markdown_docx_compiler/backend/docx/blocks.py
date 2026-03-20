"""Block-level rendering: headings, paragraphs, tables, code, etc."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from markdown_docx_compiler.backend.docx.inlines import _stringify_inline, render_inline_nodes
from markdown_docx_compiler.backend.docx.ooxml_helpers import (
    continue_list_numbering,
    restart_list_numbering,
    rgb,
    set_all_fonts,
    set_cell_shading,
    set_cell_vertical_alignment,
    set_cell_width,
    set_paragraph_bottom_border,
    set_paragraph_left_border,
    set_paragraph_shading,
    set_table_borders,
    set_table_cell_margins,
    set_table_grid,
    set_table_layout_fixed,
    set_table_width_dxa,
)
from markdown_docx_compiler.models.config import DocumentConfig
from markdown_docx_compiler.models.document import (
    BlockNode,
    Blockquote,
    CodeBlock,
    Heading,
    HorizontalRule,
    Image,
    List,
    Paragraph,
    Table,
)
from markdown_docx_compiler.models.style import BlockStyle, FontStyle, SpacingStyle

logger = logging.getLogger(__name__)


def render_block(
    *,
    doc: Any,
    block: BlockNode,
    style: BlockStyle,
    block_styles: dict[int, BlockStyle],
    config: DocumentConfig,
    content_width_inches: float,
    content_width_twips: int,
) -> None:
    """Dispatch a single block to the appropriate renderer."""
    if style.page_break_before:
        doc.add_page_break()

    if isinstance(block, Heading):
        _render_heading(doc, block, style, config)
    elif isinstance(block, Paragraph):
        _render_paragraph(doc, block, style, config)
    elif isinstance(block, List):
        _render_list(
            doc,
            block,
            style,
            block_styles,
            config,
            level=0,
            ordered_num_id=None,
            ordered_level=-1,
            ordered_scheme=None,
            content_width_inches=content_width_inches,
            content_width_twips=content_width_twips,
        )
    elif isinstance(block, Table):
        _render_table(doc, block, style, config, content_width_twips)
    elif isinstance(block, CodeBlock):
        _render_code_block(doc, block, style, config)
    elif isinstance(block, Blockquote):
        _render_blockquote(doc, block, style, config)
    elif isinstance(block, Image):
        _render_image(doc, block, style, config, content_width_inches)
    elif isinstance(block, HorizontalRule):
        _render_horizontal_rule(doc, style, config)


# ---------------------------------------------------------------------------
# Individual block renderers
# ---------------------------------------------------------------------------

# Heading size/spacing indexed by heading level (1-6).
_HEADING_SIZES: dict[int, float] = {1: 20.0, 2: 15.0, 3: 12.5, 4: 11.0, 5: 10.5, 6: 10.5}
_HEADING_BEFORE: dict[int, float] = {1: 28.0, 2: 22.0, 3: 16.0, 4: 12.0, 5: 10.0, 6: 10.0}
_HEADING_AFTER: dict[int, float] = {1: 10.0, 2: 8.0, 3: 6.0, 4: 4.0, 5: 4.0, 6: 4.0}


def _font_or(style: BlockStyle, config: DocumentConfig) -> FontStyle:
    """Resolve the effective font for a block."""
    return style.font or config.font or FontStyle()


def _render_heading(doc: Any, block: Heading, style: BlockStyle, config: DocumentConfig) -> None:
    para = doc.add_paragraph()
    sp = style.spacing or SpacingStyle()
    before = sp.before if sp.before is not None else _HEADING_BEFORE.get(block.level, 10)
    after = sp.after if sp.after is not None else _HEADING_AFTER.get(block.level, 4)
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after = Pt(after)

    font = _font_or(style, config)
    heading_font = FontStyle(
        family=font.family,
        size=font.size or _HEADING_SIZES.get(block.level, 10.5),
        color=font.color or config.font.color or "111827",
        bold=font.bold if font.bold is not None else True,
        italic=font.italic,
        underline=font.underline,
        strikethrough=font.strikethrough,
        small_caps=font.small_caps,
        all_caps=font.all_caps,
        letter_spacing=font.letter_spacing,
        highlight=font.highlight,
    )
    render_inline_nodes(
        paragraph=para,
        nodes=block.content,
        font=heading_font,
        link=style.link or config.link,
        mono_font=config.mono_font or "Consolas",
    )


def _render_paragraph(doc: Any, block: Paragraph, style: BlockStyle, config: DocumentConfig) -> None:
    para = doc.add_paragraph()
    sp = style.spacing or SpacingStyle()
    para.paragraph_format.space_before = Pt(sp.before or 0.0)
    para.paragraph_format.space_after = Pt(sp.after if sp.after is not None else 6.0)
    para.paragraph_format.line_spacing = sp.line or 1.25
    if sp.indent_left:
        para.paragraph_format.left_indent = Inches(sp.indent_left)
    if style.alignment:
        para.alignment = _alignment(style.alignment)

    if style.background:
        set_paragraph_shading(para, style.background)

    font = _font_or(style, config)
    render_inline_nodes(
        paragraph=para,
        nodes=block.content,
        font=font,
        link=style.link or config.link,
        mono_font=config.mono_font or "Consolas",
    )


def _render_list(
    doc: Any,
    block: List,
    style: BlockStyle,
    block_styles: dict[int, BlockStyle],
    config: DocumentConfig,
    *,
    level: int,
    ordered_num_id: int | None,
    ordered_level: int,
    ordered_scheme: str | None,
    content_width_inches: float,
    content_width_twips: int,
) -> None:
    sp = style.spacing or SpacingStyle()
    local_scheme = _ordered_list_numbering_scheme(style, inherited_scheme=ordered_scheme)
    current_ordered_level = ordered_level
    local_ordered_num_id = ordered_num_id
    active_ordered_scheme = ordered_scheme
    if block.ordered:
        if ordered_num_id is not None and ordered_scheme == local_scheme:
            current_ordered_level = ordered_level + 1
        else:
            current_ordered_level = 0
            local_ordered_num_id = None
        active_ordered_scheme = local_scheme

    for item in block.items:
        first_paragraph_in_item = True
        for inner in item.blocks:
            inner_style = block_styles.get(inner.meta.index, style)
            if isinstance(inner, Paragraph):
                continuation = not first_paragraph_in_item
                para = doc.add_paragraph(
                    style=_list_style_name(ordered=block.ordered, level=level, continuation=continuation)
                )
                if continuation:
                    base_indent = _continuation_indent_inches(level)
                else:
                    if block.ordered:
                        if local_ordered_num_id is None:
                            local_ordered_num_id = restart_list_numbering(
                                para,
                                scheme=local_scheme,
                                ilvl=current_ordered_level,
                            )
                        else:
                            continue_list_numbering(
                                para,
                                num_id=local_ordered_num_id,
                                ilvl=current_ordered_level,
                            )
                    base_indent = _list_indent_inches(level)
                inner_sp = inner_style.spacing or SpacingStyle()
                para.paragraph_format.left_indent = Inches(base_indent + (inner_sp.indent_left or 0.0))
                before = (
                    inner_sp.before if inner_sp.before is not None else (sp.before if sp.before is not None else 2.0)
                )
                after = inner_sp.after if inner_sp.after is not None else (sp.after if sp.after is not None else 2.0)
                para.paragraph_format.space_before = Pt(before)
                para.paragraph_format.space_after = Pt(after)
                para.paragraph_format.line_spacing = inner_sp.line or 1.25
                if inner_style.alignment:
                    para.alignment = _alignment(inner_style.alignment)
                if inner_style.background:
                    set_paragraph_shading(para, inner_style.background)
                render_inline_nodes(
                    paragraph=para,
                    nodes=inner.content,
                    font=_font_or(inner_style, config),
                    link=inner_style.link or config.link,
                    mono_font=config.mono_font or "Consolas",
                )
                first_paragraph_in_item = False
            elif isinstance(inner, List):
                _render_list(
                    doc,
                    inner,
                    inner_style,
                    block_styles,
                    config,
                    level=level + 1,
                    ordered_num_id=local_ordered_num_id,
                    ordered_level=current_ordered_level,
                    ordered_scheme=active_ordered_scheme,
                    content_width_inches=content_width_inches,
                    content_width_twips=content_width_twips,
                )
            else:
                render_block(
                    doc=doc,
                    block=inner,
                    style=inner_style,
                    block_styles=block_styles,
                    config=config,
                    content_width_inches=content_width_inches,
                    content_width_twips=content_width_twips,
                )


def _render_table(doc: Any, block: Table, style: BlockStyle, config: DocumentConfig, content_width_twips: int) -> None:
    sp = style.spacing or SpacingStyle()
    tp = style.table

    if sp.before:
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(sp.before)
        spacer.paragraph_format.line_spacing = Pt(1)

    column_widths = _table_column_widths(block, style, content_width_twips)
    table = doc.add_table(rows=1 + len(block.rows), cols=block.column_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_layout_fixed(table)
    set_table_width_dxa(table, sum(column_widths))
    set_table_grid(table, column_widths)

    border_color = (
        (tp.border_color if tp else None)
        or (style.border.top.color if style.border and style.border.top else None)
        or "D1D5DB"
    )
    set_table_borders(table, border_color)
    set_table_cell_margins(table)

    font = _font_or(style, config)
    show_header = (tp.header_row if tp else None) is not False

    for col_idx, header in enumerate(block.headers):
        cell = table.rows[0].cells[col_idx]
        set_cell_width(cell, column_widths[col_idx])
        set_cell_vertical_alignment(cell)
        if show_header:
            set_cell_shading(cell, style.background or "F3F4F6")
        para = cell.paragraphs[0]
        para.paragraph_format.space_before = Pt(3)
        para.paragraph_format.space_after = Pt(3)
        para.alignment = _alignment(block.alignments[col_idx])
        header_font = FontStyle(
            family=font.family,
            size=font.size,
            color=font.color,
            bold=True if show_header else font.bold,
        )
        render_inline_nodes(
            paragraph=para,
            nodes=header.content,
            font=header_font,
            link=style.link or config.link,
            mono_font=config.mono_font or "Consolas",
        )

    alt_color = tp.alternating_color if tp else None
    for row_idx, row in enumerate(block.rows):
        for col_idx, cell_content in enumerate(row):
            cell = table.rows[row_idx + 1].cells[col_idx]
            set_cell_width(cell, column_widths[col_idx])
            set_cell_vertical_alignment(cell)
            if alt_color and row_idx % 2 == 1:
                set_cell_shading(cell, alt_color)
            para = cell.paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            align = block.alignments[col_idx] if col_idx < len(block.alignments) else "left"
            para.alignment = _alignment(align)
            render_inline_nodes(
                paragraph=para,
                nodes=cell_content.content,
                font=font,
                link=style.link or config.link,
                mono_font=config.mono_font or "Consolas",
            )

    if sp.after:
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(sp.after)
        spacer.paragraph_format.line_spacing = Pt(1)


def _render_code_block(doc: Any, block: CodeBlock, style: BlockStyle, config: DocumentConfig) -> None:
    para = doc.add_paragraph()
    sp = style.spacing or SpacingStyle()
    para.paragraph_format.space_before = Pt(sp.before or 6.0)
    para.paragraph_format.space_after = Pt(sp.after or 6.0)
    para.paragraph_format.line_spacing = sp.line or 1.15
    set_paragraph_shading(para, style.background or "F3F4F6")
    mono = config.mono_font or "Consolas"
    font = _font_or(style, config)
    run = para.add_run(block.value)
    run.font.name = mono
    run.font.size = Pt(font.size or 9.5)
    run.font.color.rgb = rgb(font.color or "111827")
    set_all_fonts(run, mono)


def _render_blockquote(doc: Any, block: Blockquote, style: BlockStyle, config: DocumentConfig) -> None:
    para = doc.add_paragraph()
    sp = style.spacing or SpacingStyle()
    para.paragraph_format.space_before = Pt(sp.before or 8.0)
    para.paragraph_format.space_after = Pt(sp.after or 8.0)
    para.paragraph_format.left_indent = Inches(sp.indent_left or 0.3)

    border_color = "94A3B8"
    border_width = 12
    if style.border and style.border.left:
        border_color = style.border.left.color or border_color
        border_width = int((style.border.left.width or 3.0) * 4)
    set_paragraph_left_border(para, border_color, width=border_width)

    font = _font_or(style, config)
    bq_font = FontStyle(
        family=font.family,
        size=font.size,
        color=font.color or "6B7280",
        italic=font.italic if font.italic is not None else True,
    )
    render_inline_nodes(
        paragraph=para,
        nodes=block.content,
        font=bq_font,
        link=style.link or config.link,
        mono_font=config.mono_font or "Consolas",
    )


def _render_image(
    doc: Any, block: Image, style: BlockStyle, config: DocumentConfig, content_width_inches: float
) -> None:
    para = doc.add_paragraph()
    ip = style.image
    align = (ip.alignment if ip else None) or "center"
    para.alignment = _alignment(align)
    sp = style.spacing or SpacingStyle()
    para.paragraph_format.space_before = Pt(sp.before or 8.0)
    para.paragraph_format.space_after = Pt(4 if block.alt_text else 8)

    run = para.add_run()
    image_path = Path(block.path)
    if image_path.exists():
        width_str = ip.width if ip else None
        width = _parse_image_width(width_str, content_width_inches) if width_str else min(content_width_inches, 5.5)
        run.add_picture(str(image_path), width=Inches(width))
    else:
        logger.warning("Image not found, skipping: %s", image_path)

    if block.alt_text:
        caption = doc.add_paragraph()
        caption.alignment = _alignment("center")
        caption.paragraph_format.space_after = Pt(8)
        font = _font_or(style, config)
        caption_run = caption.add_run(block.alt_text)
        caption_run.font.name = font.family or "Aptos"
        caption_run.font.size = Pt(9.0)
        caption_run.font.color.rgb = rgb(font.color or "6B7280")
        caption_run.italic = True
        set_all_fonts(caption_run, font.family or "Aptos")


def _render_horizontal_rule(doc: Any, style: BlockStyle, config: DocumentConfig) -> None:
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(8)
    para.paragraph_format.line_spacing = Pt(2)
    run = para.add_run()
    run.font.size = Pt(2)
    border_color = "D1D5DB"
    if style.border and style.border.bottom:
        border_color = style.border.bottom.color or border_color
    set_paragraph_bottom_border(para, border_color)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alignment(value: str) -> WD_ALIGN_PARAGRAPH:
    mapping = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(value, WD_ALIGN_PARAGRAPH.LEFT)


def _list_style_name(*, ordered: bool, level: int, continuation: bool) -> str:
    capped_level = min(level, 2)
    base = "List Continue" if continuation else "List Number" if ordered else "List Bullet"
    return base if capped_level == 0 else f"{base} {capped_level + 1}"


def _list_indent_inches(level: int) -> float:
    return 0.35 * (level + 1)


def _continuation_indent_inches(level: int) -> float:
    if level <= 2:
        return 0.25 * (level + 1)
    return 0.75 + (0.35 * (level - 2))


def _ordered_list_numbering_scheme(style: BlockStyle, *, inherited_scheme: str | None) -> str:
    if style.list and style.list.numbering:
        return style.list.numbering
    if inherited_scheme is not None:
        return inherited_scheme
    return "decimal_hierarchical"


def _parse_image_width(spec: str, content_width: float) -> float:
    spec = spec.strip().lower()
    if spec == "auto":
        return min(content_width, 5.5)
    if spec.endswith("in"):
        try:
            return float(spec[:-2])
        except ValueError as exc:
            raise ValueError(
                f"Invalid image width spec `{spec}`. Expected `auto`, `<number>in`, or `<number>%`."
            ) from exc
    if spec.endswith("%"):
        try:
            return content_width * float(spec[:-1]) / 100.0
        except ValueError as exc:
            raise ValueError(
                f"Invalid image width spec `{spec}`. Expected `auto`, `<number>in`, or `<number>%`."
            ) from exc
    raise ValueError(f"Invalid image width spec `{spec}`. Expected `auto`, `<number>in`, or `<number>%`.")


def _table_column_widths(block: Table, style: BlockStyle, total: int) -> list[int]:
    tp = style.table
    if tp and tp.columns:
        return _parse_column_widths(tp.columns, total=total, columns=block.column_count)
    return _auto_column_widths(block, total)


def _auto_column_widths(block: Table, total: int) -> list[int]:
    max_lengths: list[int] = []
    for col in range(block.column_count):
        values = [_stringify_inline(block.headers[col].content)]
        for row in block.rows:
            if col < len(row):
                values.append(_stringify_inline(row[col].content))
        longest = max((len(re.sub(r"\s+", " ", v).strip()) for v in values), default=1)
        max_lengths.append(max(1, longest))
    combined = sum(max_lengths)
    raw = [int(total * (v / combined)) for v in max_lengths]
    delta = total - sum(raw)
    if raw:
        raw[-1] += delta
    return raw


def _parse_column_widths(specs: list[str], *, total: int, columns: int) -> list[int]:
    if len(specs) < columns:
        specs = specs + ["1fr"] * (columns - len(specs))
    specs = specs[:columns]

    fractional_total = 0.0
    absolute_total = 0
    parsed: list[tuple[str, float | int]] = []
    for spec in specs:
        value = spec.strip().lower()
        if value.endswith("fr"):
            try:
                amount = float(value[:-2] or "1")
            except ValueError as exc:
                raise ValueError(
                    f"Invalid table column width spec `{spec}`. Expected `<number>fr`, `<number>in`, or `<number>%`."
                ) from exc
            parsed.append(("fr", amount))
            fractional_total += amount
        elif value.endswith("%"):
            try:
                amount = float(value[:-1]) / 100.0
            except ValueError as exc:
                raise ValueError(
                    f"Invalid table column width spec `{spec}`. Expected `<number>fr`, `<number>in`, or `<number>%`."
                ) from exc
            width = int(total * amount)
            parsed.append(("abs", width))
            absolute_total += width
        elif value.endswith("in"):
            try:
                amount = float(value[:-2])
            except ValueError as exc:
                raise ValueError(
                    f"Invalid table column width spec `{spec}`. Expected `<number>fr`, `<number>in`, or `<number>%`."
                ) from exc
            width = int(amount * 1440)
            parsed.append(("abs", width))
            absolute_total += width
        else:
            raise ValueError(
                f"Invalid table column width spec `{spec}`. Expected `<number>fr`, `<number>in`, or `<number>%`."
            )

    remaining = max(total - absolute_total, 0)
    widths: list[int] = []
    for kind, amount in parsed:
        if kind == "abs":
            widths.append(int(amount))
        else:
            widths.append(int(remaining * (float(amount) / fractional_total)) if fractional_total else 0)
    delta = total - sum(widths)
    if widths:
        widths[-1] += delta
    return widths
