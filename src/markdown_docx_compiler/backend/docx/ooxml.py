"""Low-level OOXML helpers for precise DOCX layout control."""

from __future__ import annotations

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt, RGBColor
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run


def rgb(hex_color: str) -> RGBColor:
    value = hex_color.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def set_secondary_font(run: Run, font_name: str) -> None:
    """Set east Asia and complex-script font slots."""
    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = parse_xml(f"<w:rFonts {nsdecls('w')}/>")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:eastAsia"), font_name)
    r_fonts.set(qn("w:cs"), font_name)


def add_page_field(paragraph: Paragraph, *, font_name: str, font_size: float, color: str) -> None:
    """Insert a PAGE field with visible styling."""
    for xml_value in [
        f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>',
        f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>',
        f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>',
    ]:
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.color.rgb = rgb(color)
        set_secondary_font(run, font_name)
        run._r.append(parse_xml(xml_value))


def set_table_layout_fixed(table: Table) -> None:
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblLayout")):
        tbl_pr.remove(old)
    tbl_pr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))


def set_table_width_dxa(table: Table, width_twips: int) -> None:
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblW")):
        tbl_pr.remove(old)
    tbl_pr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{width_twips}" w:type="dxa"/>'))


def set_table_grid(table: Table, column_widths_twips: list[int]) -> None:
    for old in table._tbl.findall(qn("w:tblGrid")):
        table._tbl.remove(old)
    cols = "".join(f'<w:gridCol w:w="{width}"/>' for width in column_widths_twips)
    table._tbl.insert(1, parse_xml(f"<w:tblGrid {nsdecls('w')}>{cols}</w:tblGrid>"))


def set_table_borders(table: Table, color: str) -> None:
    """Apply full borders with Google-Docs-friendly left/right tags."""
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)
    tbl_pr.append(
        parse_xml(
            f"<w:tblBorders {nsdecls('w')}>"
            f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f"</w:tblBorders>"
        )
    )


def set_table_cell_margins(table: Table, *, top: int = 40, left: int = 80, bottom: int = 40, right: int = 80) -> None:
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblCellMar")):
        tbl_pr.remove(old)
    tbl_pr.append(
        parse_xml(
            f"<w:tblCellMar {nsdecls('w')}>"
            f'  <w:top w:w="{top}" w:type="dxa"/>'
            f'  <w:left w:w="{left}" w:type="dxa"/>'
            f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
            f'  <w:right w:w="{right}" w:type="dxa"/>'
            f"</w:tblCellMar>"
        )
    )


def set_cell_shading(cell: _Cell, color: str) -> None:
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>'))


def set_cell_width(cell: _Cell, width_twips: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:tcW")):
        tc_pr.remove(old)
    tc_pr.append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{width_twips}" w:type="dxa"/>'))


def set_cell_vertical_alignment(cell: _Cell, val: str = "center") -> None:
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="{val}"/>'))


def set_paragraph_left_border(paragraph: Paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(
        parse_xml(f'<w:pBdr {nsdecls("w")}>  <w:left w:val="single" w:sz="12" w:space="8" w:color="{color}"/></w:pBdr>')
    )


def set_paragraph_bottom_border(paragraph: Paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(
        parse_xml(
            f'<w:pBdr {nsdecls("w")}>  <w:bottom w:val="single" w:sz="4" w:space="4" w:color="{color}"/></w:pBdr>'
        )
    )


def set_paragraph_shading(paragraph: Paragraph, color: str) -> None:
    paragraph._p.get_or_add_pPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>'))
