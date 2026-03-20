"""Unit tests for the help topic system."""

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
from markdown_docx_compiler.resolve.defaults import DEFAULT_DOCUMENT

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


class TestGetHelpText:
    """Test topic routing via get_help_text()."""

    def test_none_returns_overview(self) -> None:
        text = get_help_text(None)
        assert "# markdown-docx-compiler" in text
        assert "mdc doc create" in text
        assert "<input>.docx" in text

    @pytest.mark.parametrize("topic", VALID_TOPICS)
    def test_every_valid_topic_resolves(self, topic: str) -> None:
        text = get_help_text(topic)
        assert isinstance(text, str)
        assert len(text.strip()) > 50

    def test_removed_topics_are_no_longer_valid(self) -> None:
        assert "themes" not in VALID_TOPICS
        assert "templates" not in VALID_TOPICS

    def test_unknown_topic_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown topic"):
            get_help_text("nonexistent")

    def test_value_error_lists_valid_topics(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            get_help_text("bogus")
        for topic in VALID_TOPICS:
            assert topic in str(exc_info.value)


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

    def test_has_only_document_and_spec_nouns(self, payload: dict) -> None:
        nouns = payload["nouns"]
        assert set(nouns) == {"document", "spec"}

    def test_document_noun_has_verbs(self, payload: dict) -> None:
        doc = payload["nouns"]["document"]
        assert "create" in doc["verbs"]
        assert "validate" in doc["verbs"]
        assert doc["aliases"] == ["doc"]

    def test_reference_section_exists(self, payload: dict) -> None:
        ref = payload["reference"]
        assert "sidecar_autodiscovery" in ref
        assert "anchor_syntax" in ref
        assert "builtin_document_defaults" in ref
        assert "block_types" in ref
        assert "front_matter_keys" in ref
        assert "block_style_properties" in ref
        assert "resolution_order" in ref

    def test_sidecar_autodiscovery_is_canonical(self, payload: dict) -> None:
        assert payload["reference"]["sidecar_autodiscovery"] == ["<name>.docx.yaml"]


class TestHelpJsonConsistency:
    """Ensure the payload stays in sync with the actual code objects."""

    @pytest.fixture()
    def payload(self) -> dict:
        return build_help_json()

    def test_block_style_properties_match_dataclass(self, payload: dict) -> None:
        actual = [f.name for f in dataclasses.fields(BlockStyle)]
        assert payload["reference"]["block_style_properties"] == actual

    def test_builtin_document_defaults_match_runtime_defaults(self, payload: dict) -> None:
        assert payload["reference"]["builtin_document_defaults"] == dataclasses.asdict(
            DEFAULT_DOCUMENT
        )

    def test_resolution_order_has_four_steps(self, payload: dict) -> None:
        assert len(payload["reference"]["resolution_order"]) == 4

    def test_nouns_include_document_and_spec(self, payload: dict) -> None:
        assert "document" in payload["nouns"]
        assert "spec" in payload["nouns"]


class TestHelpTopicSyntax:
    """Verify help topics reference the noun-verb CLI syntax."""

    def test_overview_uses_noun_verb(self) -> None:
        assert "mdc doc create" in OVERVIEW_TOPIC
        assert "mdc compile" not in OVERVIEW_TOPIC

    def test_sidecar_uses_noun_verb(self) -> None:
        assert "mdc doc" in HELP_TOPIC_SIDECAR
        assert "mdc compile" not in HELP_TOPIC_SIDECAR
