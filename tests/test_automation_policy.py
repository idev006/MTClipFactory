from __future__ import annotations

import pytest

from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyError, parse_fill_policies_from_pipeline_data


def test_parse_fill_policies_allows_voice_loop_to_timeline_when_enabled() -> None:
    policies = parse_fill_policies_from_pipeline_data(
        {
            "fill_policy": {
                "voiceover": {
                    "loop_enabled": True,
                    "shortfall_mode": "loop_to_timeline",
                }
            }
        },
        source_name="product_a",
    )

    assert policies.voiceover.loop_enabled is True
    assert policies.voiceover.shortfall_mode == "loop_to_timeline"


def test_parse_fill_policies_rejects_voice_loop_to_timeline_when_disabled() -> None:
    with pytest.raises(ProductAutomationPolicyError):
        parse_fill_policies_from_pipeline_data(
            {
                "fill_policy": {
                    "voiceover": {
                        "loop_enabled": False,
                        "shortfall_mode": "loop_to_timeline",
                    }
                }
            },
            source_name="product_a",
        )
