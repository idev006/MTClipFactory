from __future__ import annotations

from mt_clip_factory.factory.dto import DecisionEventDTO, OutputSummaryDTO
from mt_clip_factory.ui.factory.recipe_builder_aftercare import (
    assess_recipe_aftercare,
    build_aftercare_guidance,
    build_output_detail_lines,
    format_output_aftercare_state,
)


def _output(
    *,
    output_id: int,
    created_at: str,
    approved: bool,
    approved_at: str | None,
) -> OutputSummaryDTO:
    return OutputSummaryDTO(
        output_id=output_id,
        recipe_id=1,
        recipe_code="honey_launch",
        output_code=f"output_{output_id}",
        file_path=f"outputs/{output_id}.mp4",
        platform="tiktok",
        ratio="9:16",
        approved=approved,
        created_at=created_at,
        approved_by="qa_lead" if approved else None,
        approved_at=approved_at,
        approval_reason="approved" if approved else None,
        output_kind="preview",
        rendering_job_code=f"preview_job_{output_id}",
    )


def test_assess_recipe_aftercare_marks_historical_and_requires_rebuild() -> None:
    events = [
        DecisionEventDTO(
            event_id=1,
            recipe_id=1,
            event_type="recipe_assets_replaced",
            actor="asset_replacement_workflow",
            created_at="2026-06-13 11:00:00",
            reason="Replaced hero asset with corrected asset.",
        )
    ]
    outputs = [
        _output(output_id=1, created_at="2026-06-13 10:00:00", approved=True, approved_at="2026-06-13 10:05:00"),
        _output(output_id=2, created_at="2026-06-13 12:00:00", approved=False, approved_at=None),
    ]

    status = assess_recipe_aftercare(events, outputs)

    assert status.has_replacement is True
    assert status.requires_rebuild is True
    assert status.historical_output_ids == frozenset({1})
    assert build_aftercare_guidance(status).startswith("Replacement aftercare:")
    assert format_output_aftercare_state(outputs[0], status) == "Historical only"
    assert format_output_aftercare_state(outputs[1], status) == "Post-replacement"


def test_assess_recipe_aftercare_recognizes_post_replacement_approval() -> None:
    events = [
        DecisionEventDTO(
            event_id=1,
            recipe_id=1,
            event_type="recipe_assets_replaced",
            actor="asset_replacement_workflow",
            created_at="2026-06-13 11:00:00",
            reason="Replaced hero asset with corrected asset.",
        )
    ]
    outputs = [
        _output(output_id=2, created_at="2026-06-13 12:00:00", approved=True, approved_at="2026-06-13 12:05:00"),
    ]

    status = assess_recipe_aftercare(events, outputs)

    assert status.requires_rebuild is False
    assert status.has_post_replacement_approved_output is True
    assert "post-replacement output has already been approved" in build_aftercare_guidance(status).lower()


def test_output_detail_lines_show_history_scope_and_historical_duplicate_message(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        """
        {
          "quality": {
            "review_gate": {
              "required": true,
              "duplicate_risk": 1.0,
              "quality_score": 0.0,
              "summary": "Review required.",
              "signals": [
                {
                  "code": "historical_render_duplicate",
                  "metric_value": 1,
                  "threshold": 0
                }
              ]
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    output = OutputSummaryDTO(
        output_id=9,
        recipe_id=1,
        recipe_code="honey_launch",
        output_code="output_9",
        file_path="outputs/9.mp4",
        platform="tiktok",
        ratio="9:16",
        approved=False,
        created_at="2026-06-26 11:00:00",
        approved_by=None,
        approved_at=None,
        approval_reason=None,
        output_kind="preview",
        rendering_job_code="preview_job_9",
        manifest_path=str(manifest_path),
        duplicate_risk=1.0,
        clip_formula_hash="hash_123",
        history_scope="auto_factory_preview",
    )

    lines = build_output_detail_lines(output, None, [])

    assert "History Scope: auto_factory_preview" in lines
    assert "Clip Formula Hash: hash_123" in lines
    assert "- Historical Duplicate: This clip formula already matches usable same-product render history." in lines
