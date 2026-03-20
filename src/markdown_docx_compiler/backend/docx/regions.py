"""Region rendering: page headers, page footers, and doc headers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from markdown_docx_compiler.backend.docx.inlines import render_inline_nodes
from markdown_docx_compiler.backend.docx.ooxml_helpers import (
    add_page_field,
    rgb,
    set_all_fonts,
    set_paragraph_top_border,
)
from markdown_docx_compiler.models.config import DocumentConfig, RegionStyle
from markdown_docx_compiler.models.document import (
    ImageContent,
    Region,
    SlotContent,
    SlotItems,
    TextContent,
)
from markdown_docx_compiler.models.style import FontStyle
from markdown_docx_compiler.resolve.defaults import DEFAULT_DOCUMENT

_PAGE_VAR = "{page}"


def render_page_header(
    *,
    doc: Any,
    region: Region,
    style: RegionStyle,
    config: DocumentConfig,
) -> None:
    """Render the repeating page header into DOCX section headers."""
    if region.is_empty:
        return

    for section in doc.sections:
        header = section.header
        header.is_linked_to_previous = False
        para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT

        _render_lcr_paragraph(
            paragraph=para,
            region=region,
            style=style,
            config=config,
            content_width_twips=_content_width_twips(config),
        )


def render_page_footer(
    *,
    doc: Any,
    region: Region,
    style: RegionStyle,
    config: DocumentConfig,
) -> None:
    """Render the repeating page footer into DOCX section footers."""
    if region.is_empty:
        return

    font = style.font or config.font or FontStyle()
    font_name = font.family or config.font.family or "Aptos"
    color = font.color or "6B7280"

    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        for p in list(footer.paragraphs):
            p.clear()
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.paragraph_format.space_before = Pt(8)
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT

        if style.border and style.border.top:
            set_paragraph_top_border(para, style.border.top.color or "D1D5DB")

        content_width = _content_width_twips(config)
        p_pr = para._p.get_or_add_pPr()
        p_pr.append(
            parse_xml(
                f'<w:tabs xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'  <w:tab w:val="center" w:pos="{content_width // 2}"/>'
                f'  <w:tab w:val="right" w:pos="{content_width}"/>'
                f"</w:tabs>"
            )
        )

        sz = font.size or 8.0
        _render_slot_items_inline(
            para,
            region.left,
            font_name=font_name,
            font_size=sz,
            color=color,
            config=config,
        )
        _add_tab_run(para, font_name=font_name, font_size=sz, color=color)
        _render_slot_items_inline(
            para,
            region.center,
            font_name=font_name,
            font_size=sz,
            color=color,
            config=config,
        )
        _add_tab_run(para, font_name=font_name, font_size=sz, color=color)
        _render_slot_items_inline(
            para,
            region.right,
            font_name=font_name,
            font_size=sz,
            color=color,
            config=config,
        )


def render_doc_header(
    *,
    doc: Any,
    region: Region,
    style: RegionStyle,
    config: DocumentConfig,
) -> None:
    """Render the first-page doc header as a borderless two-column table.

    Left slot content goes in the left cell, right slot content goes in
    the right cell.  Center slot, if present, is rendered as a full-width
    paragraph above the table.
    """
    if region.is_empty:
        return

    font = style.font or config.font or FontStyle()
    font_name = font.family or config.font.family or "Aptos"
    font_size = font.size or 9.0
    font_color = font.color or "6B7280"
    mono_font = config.mono_font or "Consolas"

    if region.center:
        for item in region.center:
            _render_item_as_paragraph(
                doc,
                item,
                font_name=font_name,
                font_size=font_size,
                font_color=font_color,
                mono_font=mono_font,
                style=style,
                config=config,
            )

    if not region.left and not region.right:
        return

    content_width = _content_width_inches(config)
    left_width = content_width * 0.55
    right_width = content_width * 0.45

    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    _remove_table_borders(table)

    table.columns[0].width = Inches(left_width)
    table.columns[1].width = Inches(right_width)

    left_cell = table.cell(0, 0)
    right_cell = table.cell(0, 1)

    _render_items_into_cell(
        left_cell,
        region.left,
        font_name=font_name,
        font_size=font_size,
        font_color=font_color,
        mono_font=mono_font,
        style=style,
        config=config,
    )
    right_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _render_items_into_cell(
        right_cell,
        region.right,
        font_name=font_name,
        font_size=font_size,
        font_color=font_color,
        mono_font=mono_font,
        style=style,
        config=config,
        alignment=WD_ALIGN_PARAGRAPH.RIGHT,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _render_lcr_paragraph(
    *,
    paragraph: Any,
    region: Region,
    style: RegionStyle,
    config: DocumentConfig,
    content_width_twips: int,
) -> None:
    """Render L/C/R slots into a single paragraph using tab stops.

    Used for page header / page footer single-line layout.
    """
    font = style.font or config.font or FontStyle()
    font_name = font.family or config.font.family or "Aptos"
    size = font.size or 8.0
    color = font.color or "6B7280"

    for items in [region.left, region.center, region.right]:
        for item in items:
            if isinstance(item, ImageContent):
                run = paragraph.add_run()
                iw = style.image.width if style.image else None
                width = _parse_width(iw) if iw else 0.7
                if Path(item.path).exists():
                    run.add_picture(item.path, width=Inches(width))
                return
            if isinstance(item, TextContent):
                render_inline_nodes(
                    paragraph=paragraph,
                    nodes=item.content,
                    font=FontStyle(family=font_name, size=size, color=color),
                    link=config.link,
                    mono_font=config.mono_font or "Consolas",
                )
                return


def _render_slot_items_inline(
    paragraph: Any,
    items: SlotItems,
    *,
    font_name: str,
    font_size: float,
    color: str,
    config: DocumentConfig,
) -> None:
    """Render all items in a slot inline within one paragraph (for footer L/C/R)."""
    for item in items:
        _render_single_slot_content(
            paragraph,
            item,
            font_name=font_name,
            font_size=font_size,
            color=color,
            config=config,
        )


def _render_single_slot_content(
    paragraph: Any,
    item: SlotContent,
    *,
    font_name: str,
    font_size: float,
    color: str,
    config: DocumentConfig,
) -> None:
    """Render a single SlotContent item into the given paragraph."""
    if isinstance(item, TextContent):
        has_page_var = any(hasattr(n, "text") and _PAGE_VAR in getattr(n, "text", "") for n in item.content)
        if has_page_var:
            add_page_field(
                paragraph,
                font_name=font_name,
                font_size=font_size,
                color=color,
            )
        else:
            render_inline_nodes(
                paragraph=paragraph,
                nodes=item.content,
                font=FontStyle(family=font_name, size=font_size, color=color),
                link=config.link,
                mono_font=config.mono_font or "Consolas",
            )
    elif isinstance(item, ImageContent):
        run = paragraph.add_run()
        if Path(item.path).exists():
            run.add_picture(item.path, width=Inches(0.5))


def _add_tab_run(
    paragraph: Any,
    *,
    font_name: str,
    font_size: float,
    color: str,
) -> None:
    run = paragraph.add_run("\t")
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.color.rgb = rgb(color)
    set_all_fonts(run, font_name)


def _render_item_as_paragraph(
    doc: Any,
    item: SlotContent,
    *,
    font_name: str,
    font_size: float,
    font_color: str,
    mono_font: str,
    style: RegionStyle,
    config: DocumentConfig,
) -> None:
    """Render a single slot item as a full-width body paragraph."""
    if isinstance(item, ImageContent):
        para = doc.add_paragraph()
        run = para.add_run()
        iw = style.image.width if style.image else None
        width = _parse_width(iw) if iw else 0.7
        if Path(item.path).exists():
            run.add_picture(item.path, width=Inches(width))
    elif isinstance(item, TextContent):
        para = doc.add_paragraph()
        para.paragraph_format.space_after = Pt(2)
        render_inline_nodes(
            paragraph=para,
            nodes=item.content,
            font=FontStyle(family=font_name, size=font_size, color=font_color),
            link=config.link,
            mono_font=mono_font,
        )


def _render_items_into_cell(
    cell: Any,
    items: SlotItems,
    *,
    font_name: str,
    font_size: float,
    font_color: str,
    mono_font: str,
    style: RegionStyle,
    config: DocumentConfig,
    alignment: int | None = None,
) -> None:
    """Render a list of slot items into a table cell, one paragraph per item."""
    first = True
    for item in items:
        if first:
            para = cell.paragraphs[0]
            first = False
        else:
            para = cell.add_paragraph()

        if alignment is not None:
            para.alignment = alignment

        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(2)

        if isinstance(item, ImageContent):
            run = para.add_run()
            iw = style.image.width if style.image else None
            width = _parse_width(iw) if iw else 0.7
            if Path(item.path).exists():
                run.add_picture(item.path, width=Inches(width))
        elif isinstance(item, TextContent):
            render_inline_nodes(
                paragraph=para,
                nodes=item.content,
                font=FontStyle(
                    family=font_name,
                    size=font_size,
                    color=font_color,
                ),
                link=config.link,
                mono_font=mono_font,
            )


def _remove_table_borders(table: Any) -> None:
    """Strip all borders from a DOCX table to make it invisible."""
    tbl = table._tbl
    tbl_pr = (
        tbl.tblPr
        if tbl.tblPr is not None
        else parse_xml('<w:tblPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
    )
    borders = parse_xml(
        '<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '  <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        "</w:tblBorders>"
    )
    existing = tbl_pr.find(qn("w:tblBorders"))
    if existing is not None:
        tbl_pr.remove(existing)
    tbl_pr.append(borders)

    for cell in tbl.iter_tcs():
        tc_pr = cell.tcPr
        if tc_pr is None:
            tc_pr = parse_xml('<w:tcPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
            cell.insert(0, tc_pr)
        cell_borders = parse_xml(
            '<w:tcBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '  <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            "</w:tcBorders>"
        )
        existing_cb = tc_pr.find(qn("w:tcBorders"))
        if existing_cb is not None:
            tc_pr.remove(existing_cb)
        tc_pr.append(cell_borders)

    for cell in tbl.iter_tcs():
        tc_pr = cell.tcPr
        if tc_pr is not None:
            margins = parse_xml(
                '<w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '  <w:top w:w="0" w:type="dxa"/>'
                '  <w:left w:w="0" w:type="dxa"/>'
                '  <w:bottom w:w="0" w:type="dxa"/>'
                '  <w:right w:w="0" w:type="dxa"/>'
                "</w:tcMar>"
            )
            tc_pr.append(margins)


def _content_width_twips(config: DocumentConfig) -> int:
    _d = DEFAULT_DOCUMENT
    total = config.page.width_inches or _d.page.width_inches or 8.5
    left = config.page.margin.left or _d.page.margin.left or 1.0
    right = config.page.margin.right or _d.page.margin.right or 1.0
    return int((total - left - right) * 1440)


def _content_width_inches(config: DocumentConfig) -> float:
    _d = DEFAULT_DOCUMENT
    total = config.page.width_inches or _d.page.width_inches or 8.5
    left = config.page.margin.left or _d.page.margin.left or 1.0
    right = config.page.margin.right or _d.page.margin.right or 1.0
    return total - left - right


def _parse_width(spec: str) -> float:
    spec = spec.strip().lower()
    if spec.endswith("in"):
        return float(spec[:-2])
    return 0.7
