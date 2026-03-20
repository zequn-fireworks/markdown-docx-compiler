"""Configuration models for the sidecar and document settings.

``SidecarConfig`` is the parsed representation of a ``.docx.yaml`` sidecar
file.  ``DocumentConfig`` holds resolved page-level settings (margins, page
size).  Both are frozen dataclasses assembled during the loading phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from markdown_docx_compiler.models.style import (
    BlockStyle,
    BorderStyle,
    FontStyle,
    ImageProps,
    LinkStyle,
)

# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarginConfig:
    top: float | None = None  # inches
    bottom: float | None = None
    left: float | None = None
    right: float | None = None


@dataclass(frozen=True)
class PageConfig:
    width_inches: float | None = None
    margin: MarginConfig = field(default_factory=MarginConfig)


# ---------------------------------------------------------------------------
# Document-level settings (tier 1 of cascade)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentConfig:
    """Top-level document settings from the ``document:`` sidecar section."""

    title: str | None = None

    font: FontStyle = field(default_factory=FontStyle)
    mono_font: str | None = None
    link: LinkStyle = field(default_factory=LinkStyle)

    page: PageConfig = field(default_factory=PageConfig)


# ---------------------------------------------------------------------------
# Region styling
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegionStyle:
    """Style applied to a document region (page header, footer, doc header).

    Inherits font/color from ``DocumentConfig`` when not specified.
    """

    font: FontStyle | None = None
    border: BorderStyle | None = None
    image: ImageProps | None = None


# ---------------------------------------------------------------------------
# Block instance override
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockOverride:
    """Instance-level style override keyed by anchor ID.

    The optional ``type`` field makes inheritance explicit and enables
    validation against the actual IR block type.
    """

    type: str | None = None
    style: BlockStyle = field(default_factory=BlockStyle)


# ---------------------------------------------------------------------------
# Sidecar config (the whole .docx.yaml file)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SidecarConfig:
    """Parsed representation of a sidecar YAML file."""

    inherits: str | None = None

    document: DocumentConfig = field(default_factory=DocumentConfig)

    page_header: RegionStyle = field(default_factory=RegionStyle)
    page_footer: RegionStyle = field(default_factory=RegionStyle)
    doc_header: RegionStyle = field(default_factory=RegionStyle)

    defaults: dict[str, BlockStyle] = field(default_factory=dict)
    blocks: dict[str, BlockOverride] = field(default_factory=dict)
