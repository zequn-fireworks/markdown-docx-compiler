"""Help topic aggregator for the mdc CLI.

Each topic's prose is co-located with the domain module that owns it.
This module collects them into a single registry.  In the noun-verb
CLI the topics are wired into each noun's ``--help`` epilog, but this
module still exposes the topic registry for programmatic access and testing.
"""

from __future__ import annotations

from typing import Any

from markdown_docx_compiler import HELP_TOPIC as _OVERVIEW
from markdown_docx_compiler.cli._document import HELP_TOPIC_MARKDOWN as _MARKDOWN
from markdown_docx_compiler.parser.front_matter import HELP_TOPIC as _FRONTMATTER
from markdown_docx_compiler.parser.markdown import (
    HELP_TOPIC_ANCHORS as _ANCHORS,
)

HELP_TOPIC_SIDECAR = """\
# Sidecar Config

A sidecar YAML file controls styling and layout for a compiled document.
Place it next to your markdown file as ``<name>.docx.yaml``.

## Structure

  inherits: ../base.docx.yaml  # inherit from another sidecar file

  document:
    title: My Report
    font: { family: Arial, size: 11, color: "333333" }
    mono_font: Consolas
    link: { color: "2563EB" }
    page:
      width_inches: 8.5
      margin: { top: 1.0, bottom: 0.8, left: 1.0, right: 1.0 }

  page_header:
    font: { size: 8, color: "999999" }

  page_footer:
    font: { size: 8, color: "666666" }

  defaults:
    paragraph:
      spacing: { after: 6, line: 1.15 }
    table:
      table: { header_row: true, columns: [1fr, 2fr] }
    code:
      font: { size: 9.5 }
      background: "F3F4F6"

  blocks:
    my-anchor-id:
      type: table
      table: { columns: [3fr, 1fr, 1fr] }

## Resolution order

  1. Built-in defaults
  2. Sidecar document globals + type defaults
  3. Sidecar block instance overrides (by anchor)
  4. Front matter overrides

## Auto-discovery

The compiler looks for sidecars next to the markdown file:

  report.md  ->  report.docx.yaml

Use ``mdc spec show --for report.md`` to check which sidecar is found.
Use ``mdc doc create report.md --spec custom.docx.yaml`` to override.
"""

TOPIC_INDEX: list[tuple[str, str]] = [
    ("markdown", "Supported markdown features and constraints"),
    ("frontmatter", "Front matter keys for document metadata"),
    ("sidecar", "Sidecar config structure and resolution order"),
    ("anchors", "HTML comment anchor syntax"),
]

VALID_TOPICS: list[str] = [name for name, _ in TOPIC_INDEX]

_STATIC_TOPICS: dict[str, str] = {
    "markdown": _MARKDOWN,
    "frontmatter": _FRONTMATTER,
    "sidecar": HELP_TOPIC_SIDECAR,
    "anchors": _ANCHORS,
}

NOUN_TOPIC_MAP: dict[str, list[str]] = {
    "document": ["markdown", "anchors"],
    "document create": ["frontmatter"],
    "spec": ["sidecar"],
}


def get_help_text(topic: str | None = None) -> str:
    """Return help text for a topic, or the overview when *topic* is None.

    Args:
        topic: Topic name, or None for the overview.

    Returns:
        The help text string for the requested topic.

    Raises:
        ValueError: If *topic* is not a recognized topic name.
    """
    if topic is None:
        return _OVERVIEW

    if topic in _STATIC_TOPICS:
        return _STATIC_TOPICS[topic]

    valid = ", ".join(VALID_TOPICS)
    raise ValueError(f"Unknown topic: {topic}\nAvailable topics: {valid}")


def build_help_json() -> dict[str, Any]:
    """Build the machine-readable discovery payload.

    This wraps :func:`markdown_docx_compiler.cli._discovery.build_discovery_payload`
    for backward compatibility.
    """
    from markdown_docx_compiler.cli._discovery import build_discovery_payload

    return build_discovery_payload()
