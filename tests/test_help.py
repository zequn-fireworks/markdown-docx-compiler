"""Unit tests for the help topic system.

Tests help text aggregation, discovery payload correctness, topic routing,
and consistency between the help output and actual code objects.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from markdown_docx_compiler import HELP_TOPIC as OVERVIEW_TOPIC
from markdown_docx_compiler.help_text import (
    HELP_TOPIC_SIDECAR,
    VALID_TOPICS,
    build_help_json,
    get_help_text,
)
from markdown_docx_compiler.models.style import BlockStyle
from markdown_docx_compiler.parser.front_matter import HELP_TOPIC as FM_TOPIC
from markdown_docx_compiler.parser.markdown import (
    HELP_TOPIC_ANCHORS,
    HELP_TOPIC_MARKDOWN,
)
from markdown_docx_compiler.styles.themes import DEFAULT_THEME
from markdown_docx_compiler.styles.themes import help_topic as themes_help_topic

# ---------------------------------------------------------------------------
# HELP_TOPIC existence and non-emptiness
# ---------------------------------------------------------------------------

_MODULE_TOPICS = {
    "__init__": OVERVIEW_TOPIC,
    "sidecar": HELP_TOPIC_SIDECAR,
    "front_matter": FM_TOPIC,
    "markdown (markdown)": HELP_TOPIC_MARKDOWN,
    "markdown (anchors)": HELP_TOPIC_ANCHORS,
}


class TestHelpTopicConstants:
    """Every domain module must export a non-empty HELP_TOPIC string."""

    @pytest.mark.parametrize(
        "module_name,topic_text",
        list(_MODULE_TOPICS.items()),
        ids=list(_MODULE_TOPICS.keys()),
    )
    def test_help_topic_is_nonempty_string(self, module_name: str, topic_text: str) -> None:
        assert isinstance(topic_text, str)
        assert len(topic_text.strip()) > 0

    def test_themes_help_topic_returns_nonempty_string(self) -> None:
        text = themes_help_topic()
        assert isinstance(text, str)
        assert len(text.strip()) > 0


# ---------------------------------------------------------------------------
# get_help_text routing
# ---------------------------------------------------------------------------


class TestGetHelpText:
    """Test topic routing via get_help_text()."""

    def test_none_returns_overview(self) -> None:
        text = get_help_text(None)
        assert "# markdown-docx-compiler" in text
        assert "mdc doc create" in text

    @pytest.mark.parametrize("topic", VALID_TOPICS)
    def test_every_valid_topic_resolves(self, topic: str) -> None:
        text = get_help_text(topic)
        assert isinstance(text, str)
        assert len(text.strip()) > 50

    def test_themes_topic_includes_default_brand(self) -> None:
        text = get_help_text("themes")
        assert DEFAULT_THEME.document.font in text

    def test_templates_topic_avoids_nonexistent_template_flag(self) -> None:
        text = get_help_text("templates")
        assert "--template" not in text
        assert "mdc template list" in text

    def test_unknown_topic_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown topic"):
            get_help_text("nonexistent")

    def test_value_error_lists_valid_topics(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            get_help_text("bogus")
        for topic in VALID_TOPICS:
            assert topic in str(exc_info.value)


# ---------------------------------------------------------------------------
# themes help_topic()
# ---------------------------------------------------------------------------


class TestThemesHelpTopic:
    """Test the dynamically generated themes help text."""

    def test_contains_default_brand_info(self) -> None:
        text = themes_help_topic()
        assert DEFAULT_THEME.document.font in text
        assert DEFAULT_THEME.document.mono_font in text

    def test_contains_variants(self) -> None:
        text = themes_help_topic()
        assert "Variants:" in text
        assert "body" in text
        assert "lead" in text


# ---------------------------------------------------------------------------
# build_help_json / discovery payload structure
# ---------------------------------------------------------------------------


class TestBuildHelpJson:
    """Test the machine-readable discovery payload."""

    @pytest.fixture()
    def payload(self) -> dict:
        return build_help_json()

    def test_is_json_serializable(self, payload: dict) -> None:
        serialized = json.dumps(payload)
        roundtripped = json.loads(serialized)
        assert roundtripped == payload

    def test_has_version(self, payload: dict) -> None:
        assert "version" in payload

    def test_has_nouns(self, payload: dict) -> None:
        nouns = payload["nouns"]
        assert "document" in nouns
        assert "spec" in nouns
        assert "template" in nouns
        assert "theme" in nouns

    def test_document_noun_has_verbs(self, payload: dict) -> None:
        doc = payload["nouns"]["document"]
        assert "create" in doc["verbs"]
        assert "validate" in doc["verbs"]
        assert doc["aliases"] == ["doc"]

    def test_reference_section_exists(self, payload: dict) -> None:
        ref = payload["reference"]
        assert "sidecar_autodiscovery" in ref
        assert "anchor_syntax" in ref
        assert "default_brand" in ref
        assert "block_types" in ref
        assert "front_matter_keys" in ref
        assert "block_style_properties" in ref
        assert "resolution_order" in ref


# ---------------------------------------------------------------------------
# Consistency: discovery payload stays in sync with actual code
# ---------------------------------------------------------------------------


class TestHelpJsonConsistency:
    """Ensure the payload reflects the actual dataclass fields and
    default brand, so help never drifts from the code.
    """

    @pytest.fixture()
    def payload(self) -> dict:
        return build_help_json()

    def test_block_style_properties_match_dataclass(self, payload: dict) -> None:
        actual = [f.name for f in dataclasses.fields(BlockStyle)]
        assert payload["reference"]["block_style_properties"] == actual

    def test_default_brand_font_matches(self, payload: dict) -> None:
        assert payload["reference"]["default_brand"]["font"] == DEFAULT_THEME.document.font

    def test_default_brand_has_variants(self, payload: dict) -> None:
        assert "variants" in payload["reference"]["default_brand"]
        assert "paragraph" in payload["reference"]["default_brand"]["variants"]

    def test_resolution_order_has_four_steps(self, payload: dict) -> None:
        assert len(payload["reference"]["resolution_order"]) == 4

    def test_nouns_include_document_and_spec(self, payload: dict) -> None:
        assert "document" in payload["nouns"]
        assert "spec" in payload["nouns"]


# ---------------------------------------------------------------------------
# HELP_TOPIC references new CLI syntax
# ---------------------------------------------------------------------------


class TestHelpTopicSyntax:
    """Verify help topics reference the new noun-verb CLI syntax."""

    def test_overview_uses_noun_verb(self) -> None:
        assert "mdc doc create" in OVERVIEW_TOPIC
        assert "mdc compile" not in OVERVIEW_TOPIC

    def test_sidecar_uses_noun_verb(self) -> None:
        assert "mdc doc" in HELP_TOPIC_SIDECAR
        assert "mdc compile" not in HELP_TOPIC_SIDECAR
