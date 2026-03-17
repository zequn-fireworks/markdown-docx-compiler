"""Help topic aggregator for the mdc CLI.

Each topic's prose is co-located with the domain module that owns it.
This module collects them into a single registry.  In the new noun-verb
CLI the topics are wired into each noun's ``--help`` epilog rather than
a separate ``help`` subcommand, but this module still exposes the topic
registry for programmatic access and testing.
"""

from __future__ import annotations

from typing import Any

from markdown_docx_compiler import HELP_TOPIC as _OVERVIEW
from markdown_docx_compiler.parser.front_matter import HELP_TOPIC as _FRONTMATTER
from markdown_docx_compiler.parser.markdown_parser import (
    HELP_TOPIC_ANCHORS as _ANCHORS,
)
from markdown_docx_compiler.parser.markdown_parser import (
    HELP_TOPIC_MARKDOWN as _MARKDOWN,
)
from markdown_docx_compiler.selectors import HELP_TOPIC as _SELECTORS
from markdown_docx_compiler.sidecar import HELP_TOPIC as _SIDECAR

TOPIC_INDEX: list[tuple[str, str]] = [
    ("markdown", "Supported markdown features and constraints"),
    ("frontmatter", "Front matter keys for document metadata"),
    ("sidecar", "Sidecar config structure and resolution order"),
    ("selectors", "Selector matching rules and fields"),
    ("themes", "Built-in brand, installed templates, and variants"),
    ("templates", "Installable template packages and usage"),
    ("anchors", "HTML comment anchor syntax"),
]

VALID_TOPICS: list[str] = [name for name, _ in TOPIC_INDEX]

_STATIC_TOPICS: dict[str, str] = {
    "markdown": _MARKDOWN,
    "frontmatter": _FRONTMATTER,
    "sidecar": _SIDECAR,
    "selectors": _SELECTORS,
    "anchors": _ANCHORS,
}

NOUN_TOPIC_MAP: dict[str, list[str]] = {
    "document": ["markdown", "anchors"],
    "document create": ["frontmatter"],
    "spec": ["sidecar", "selectors"],
    "template": ["templates"],
    "theme": ["themes"],
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

    if topic == "themes":
        from markdown_docx_compiler.styles.themes import help_topic

        return help_topic()

    if topic == "templates":
        from markdown_docx_compiler.styles.themes import templates_help_topic

        return templates_help_topic()

    valid = ", ".join(VALID_TOPICS)
    raise ValueError(f"Unknown topic: {topic}\nAvailable topics: {valid}")


def build_help_json() -> dict[str, Any]:
    """Build the machine-readable discovery payload.

    This wraps :func:`markdown_docx_compiler.cli._discovery.build_discovery_payload`
    for backward compatibility.
    """
    from markdown_docx_compiler.cli._discovery import build_discovery_payload

    return build_discovery_payload()
