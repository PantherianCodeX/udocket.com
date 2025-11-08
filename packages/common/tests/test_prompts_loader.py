from __future__ import annotations

import pytest

from packages.common import prompts


def test_load_prompt_with_exact_locale() -> None:
    render = prompts.render_prompt_with_meta(
        domain="analyze",
        key="system_summary",
        locale="en-CA",
        context={"transcript_language": "English", "case_type": "civil"},
    )
    assert render.resource.locale == "en-CA"
    assert render.resource.sha256
    assert "Canadian legal analyst" in render.text
    assert (
        render.text
        == "You are a Canadian legal analyst preparing a English summary for the Analyze agent.\n"
        "Focus on the civil context when assessing issues."
    )


def test_load_prompt_with_locale_fallback() -> None:
    render = prompts.render_prompt_with_meta(
        domain="analyze",
        key="system_summary",
        locale="en-US",
        context={"transcript_language": "English"},
    )
    # en-US falls back to language-level "en"
    assert render.resource.locale == "en"
    assert "Analyze agent" in render.text
    assert render.text == "You are preparing a English case summary for the Analyze agent."


def test_render_prompt_missing_required_placeholder() -> None:
    with pytest.raises(ValueError, match="Missing required prompt variables"):
        prompts.render_prompt(
            "analyze",
            "system_summary",
            locale="en-CA",
            context={},
        )


def test_prompt_lint_is_clean() -> None:
    lint_fn = getattr(prompts, "_lint_prompts")
    failures = lint_fn()
    assert failures == []
