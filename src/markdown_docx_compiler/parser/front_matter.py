"""Front matter helpers."""

from __future__ import annotations

import re
from typing import Any

import yaml

HELP_TOPIC = """\
# Front Matter

Use YAML front matter for document-level metadata.  Front matter overrides
built-in defaults but is itself overridden by sidecar config.

## Example

  ---
  title: Benchmark Report
  font: Arial
  text_color: "333333"
  ---

## Supported keys

  title                str    Document title
  font                 str    Body font family name
  mono_font            str    Monospace font name
  text_color           str    Hex color for body text (e.g. "333333")
  link_color           str    Hex color for links (e.g. "2563EB")
  page_width_inches    float  Page width in inches (default 8.5)
  margin_top           float  Top margin in inches
  margin_bottom        float  Bottom margin in inches
  margin_left          float  Left margin in inches
  margin_right         float  Right margin in inches

Note: for advanced layout (logos, footers, headers, per-block styling),
use region tags in markdown and a sidecar YAML.  See `mdc doc --help`.
"""

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.+?)\n---\s*\n", re.DOTALL)


def extract_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Return front matter and remaining markdown body."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[match.end() :]
