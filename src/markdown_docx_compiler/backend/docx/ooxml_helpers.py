"""Low-level OOXML helpers for precise DOCX layout control.

These operate directly on python-docx XML elements where the high-level
API doesn't expose enough granularity.
"""

from __future__ import annotations

from typing import Any, cast

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt, RGBColor
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.text.run import Run


def rgb(hex_color: str) -> RGBColor:
    value = hex_color.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def set_all_fonts(run: Run, font_name: str) -> None:
    """Set ascii, east-Asia, and complex-script font slots on a run."""
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
        set_all_fonts(run, font_name)
        run._r.append(parse_xml(xml_value))


def add_hyperlink_run(paragraph: Paragraph, *, text: str, url: str) -> Run:
    """Append a real external hyperlink run to a paragraph and return the run."""
    relationship_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)

    run_element = OxmlElement("w:r")
    hyperlink.append(run_element)
    paragraph._p.append(hyperlink)

    run = Run(run_element, paragraph)
    run.text = text
    return run


# -- Table helpers ---------------------------------------------------------


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
    cols = "".join(f'<w:gridCol w:w="{w}"/>' for w in column_widths_twips)
    table._tbl.insert(1, parse_xml(f"<w:tblGrid {nsdecls('w')}>{cols}</w:tblGrid>"))


def set_table_borders(table: Table, color: str) -> None:
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


# -- Cell helpers ----------------------------------------------------------


def set_cell_shading(cell: _Cell, color: str) -> None:
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>'))


def set_cell_width(cell: _Cell, width_twips: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:tcW")):
        tc_pr.remove(old)
    tc_pr.append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="{width_twips}" w:type="dxa"/>'))


def set_cell_vertical_alignment(cell: _Cell, val: str = "center") -> None:
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:vAlign {nsdecls("w")} w:val="{val}"/>'))


# -- Numbering helpers -----------------------------------------------------


def restart_list_numbering(paragraph: Paragraph, *, scheme: str, ilvl: int) -> int:
    """Create a fresh numbering sequence for the paragraph."""
    numbering_part = cast(Any, paragraph.part).numbering_part
    numbering = numbering_part.element
    abstract_num_id = _ensure_abstract_num_id(numbering, scheme=scheme)
    current_ids = [int(num.get(qn("w:numId"))) for num in numbering.findall(qn("w:num"))]
    new_num_id = (max(current_ids) + 1) if current_ids else 1

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(new_num_id))
    abstract = OxmlElement("w:abstractNumId")
    abstract.set(qn("w:val"), str(abstract_num_id))
    num.append(abstract)
    for level in range(9):
        lvl_override = OxmlElement("w:lvlOverride")
        lvl_override.set(qn("w:ilvl"), str(level))
        start_override = OxmlElement("w:startOverride")
        start_override.set(qn("w:val"), "1")
        lvl_override.append(start_override)
        num.append(lvl_override)
    numbering.append(num)

    continue_list_numbering(paragraph, num_id=new_num_id, ilvl=ilvl)
    return new_num_id


def continue_list_numbering(paragraph: Paragraph, *, num_id: int, ilvl: int) -> None:
    """Attach an existing numbering sequence to a paragraph."""
    p_pr = paragraph._p.get_or_add_pPr()
    for old in p_pr.findall(qn("w:numPr")):
        p_pr.remove(old)

    num_pr = OxmlElement("w:numPr")
    ilvl_el = OxmlElement("w:ilvl")
    ilvl_el.set(qn("w:val"), str(ilvl))
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_pr.append(ilvl_el)
    num_pr.append(num)
    p_pr.append(num_pr)


def _ensure_abstract_num_id(numbering: Any, *, scheme: str) -> int:
    name_value = f"mdc-{scheme}"
    for abstract in numbering.findall(qn("w:abstractNum")):
        name = abstract.find(qn("w:name"))
        if name is not None and name.get(qn("w:val")) == name_value:
            value = abstract.get(qn("w:abstractNumId"))
            if value is not None:
                return int(value)

    current_ids = [int(abstract.get(qn("w:abstractNumId"))) for abstract in numbering.findall(qn("w:abstractNum"))]
    abstract_num_id = (max(current_ids) + 1) if current_ids else 0
    numbering.append(_build_abstract_num(abstract_num_id=abstract_num_id, scheme=scheme))
    return abstract_num_id


def _build_abstract_num(*, abstract_num_id: int, scheme: str) -> Any:
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_num_id))

    name = OxmlElement("w:name")
    name.set(qn("w:val"), f"mdc-{scheme}")
    abstract.append(name)

    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "multilevel")
    abstract.append(multi)

    for level in range(9):
        num_fmt, lvl_text = _numbering_level_spec(scheme=scheme, level=level)
        left = int((0.35 * (level + 1)) * 1440)

        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(level))

        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")
        lvl.append(start)

        num_format = OxmlElement("w:numFmt")
        num_format.set(qn("w:val"), num_fmt)
        lvl.append(num_format)

        lvl_text_el = OxmlElement("w:lvlText")
        lvl_text_el.set(qn("w:val"), lvl_text)
        lvl.append(lvl_text_el)

        lvl_jc = OxmlElement("w:lvlJc")
        lvl_jc.set(qn("w:val"), "left")
        lvl.append(lvl_jc)

        lvl.append(
            parse_xml(
                f'<w:pPr {nsdecls("w")}>'
                f'<w:tabs><w:tab w:val="num" w:pos="{left}"/></w:tabs>'
                f'<w:ind w:left="{left}" w:hanging="360"/>'
                f"</w:pPr>"
            )
        )
        abstract.append(lvl)

    return abstract


def _numbering_level_spec(*, scheme: str, level: int) -> tuple[str, str]:
    if scheme == "alpha_hierarchical":
        return _alpha_hierarchical_spec(level)
    if scheme == "alpha_paren_hierarchical":
        return _alpha_paren_hierarchical_spec(level)
    return _decimal_hierarchical_spec(level)


def _decimal_hierarchical_spec(level: int) -> tuple[str, str]:
    if level == 0:
        return "decimal", "%1."
    parts = ".".join(f"%{idx}" for idx in range(1, level + 2))
    return "decimal", parts


def _alpha_hierarchical_spec(level: int) -> tuple[str, str]:
    if level == 0:
        return "decimal", "%1."
    if level == 1:
        return "lowerLetter", "%1.%2"
    if level == 2:
        return "lowerRoman", "%1.%2.%3"
    parts = ".".join(f"%{idx}" for idx in range(1, level + 2))
    return "decimal", parts


def _alpha_paren_hierarchical_spec(level: int) -> tuple[str, str]:
    if level == 0:
        return "decimal", "%1."
    if level == 1:
        return "lowerLetter", "%1(%2)"
    if level == 2:
        return "lowerRoman", "%1(%2)(%3)"
    parts = ".".join(f"%{idx}" for idx in range(4, level + 2))
    suffix = f".{parts}" if parts else ""
    return "decimal", f"%1(%2)(%3){suffix}"


# -- Paragraph helpers -----------------------------------------------------


def set_paragraph_shading(paragraph: Paragraph, color: str) -> None:
    paragraph._p.get_or_add_pPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}" w:val="clear"/>'))


def set_paragraph_left_border(paragraph: Paragraph, color: str, *, width: int = 12) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(
        parse_xml(
            f'<w:pBdr {nsdecls("w")}>  <w:left w:val="single" w:sz="{width}" w:space="8" w:color="{color}"/></w:pBdr>'
        )
    )


def set_paragraph_bottom_border(paragraph: Paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(
        parse_xml(
            f'<w:pBdr {nsdecls("w")}>  <w:bottom w:val="single" w:sz="4" w:space="4" w:color="{color}"/></w:pBdr>'
        )
    )


def set_paragraph_top_border(paragraph: Paragraph, color: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_pr.append(
        parse_xml(f'<w:pBdr {nsdecls("w")}>  <w:top w:val="single" w:sz="4" w:space="4" w:color="{color}"/></w:pBdr>')
    )
