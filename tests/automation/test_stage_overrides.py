from __future__ import annotations

from packages.common.agents import (
    StageKey,
    StageOverrideConfig,
    parse_stage_overrides,
    stage_overrides_to_json,
)


def test_parse_stage_overrides_handles_aliases() -> None:
    overrides = parse_stage_overrides({
        "analyze.extract_outline": {"providers": ["Azure"], "model": "gpt"},
        "build_timeline_seeds": {"provider": "openai", "max_tokens": "2000"},
        "compose.client.draft": {"provider": "azure"},
    })
    assert StageKey.AN_OUTLINE_DRAFT in overrides
    assert StageKey.AN_TIMELINE_BUILD in overrides
    assert StageKey.CO_CLIENT_DRAFT in overrides
    outline = overrides[StageKey.AN_OUTLINE_DRAFT]
    assert outline.providers == ("azure",)
    assert outline.model == "gpt"
    timeline = overrides[StageKey.AN_TIMELINE_BUILD]
    assert timeline.providers == ("openai",)
    assert timeline.max_tokens == 2000
    assert overrides[StageKey.CO_CLIENT_DRAFT].providers == ("azure",)


def test_stage_overrides_to_json_serializes_values() -> None:
    config = StageOverrideConfig(providers=("azure",), model="gpt", max_tokens=1000)
    payload = stage_overrides_to_json({StageKey.AN_OUTLINE_DRAFT: config})
    assert payload[StageKey.AN_OUTLINE_DRAFT.value]["providers"] == ["azure"]
    assert payload[StageKey.AN_OUTLINE_DRAFT.value]["model"] == "gpt"
    assert payload[StageKey.AN_OUTLINE_DRAFT.value]["max_tokens"] == 1000
