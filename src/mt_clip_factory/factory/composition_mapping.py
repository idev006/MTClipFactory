from __future__ import annotations

from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.domain.render_decisions import RenderDecision
from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.dto import (
    CompositionLayerDTO,
    CompositionPlanDTO,
    RenderDecisionDTO,
    TimelineSegmentDTO,
)


def bind_render_decision(decision: RenderDecision, *, composition_plan_id: int) -> RenderDecision:
    decision.composition_plan_id = composition_plan_id
    return decision


def bind_timeline_segment(segment: TimelineSegment, *, composition_plan_id: int) -> TimelineSegment:
    segment.composition_plan_id = composition_plan_id
    return segment


def to_composition_plan_dto(
    plan: CompositionPlan,
    segments: tuple[TimelineSegment, ...],
    decisions: tuple[RenderDecision, ...],
    *,
    format_timestamp,
) -> CompositionPlanDTO:
    return CompositionPlanDTO(
        plan_id=plan.id or 0,
        recipe_id=plan.recipe_id,
        duration_source=plan.duration_source,
        target_duration_sec=plan.target_duration_sec,
        resolved_duration_sec=plan.resolved_duration_sec,
        updated_at=format_timestamp(plan.updated_at),
        layers=tuple(
            CompositionLayerDTO(
                layer_name=layer.layer_name,
                asset_ids=layer.asset_ids,
                asset_codes=layer.asset_codes,
            )
            for layer in plan.layer_assignments
        ),
        segments=tuple(
            TimelineSegmentDTO(
                segment_id=segment.id or 0,
                segment_type=segment.segment_type,
                sequence_index=segment.sequence_index,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                target_duration_sec=segment.target_duration_sec,
                message_text=segment.message_text,
                text_rule=segment.text_rule,
                audio_policy=segment.audio_policy,
                preferred_layers=segment.preferred_layers,
            )
            for segment in segments
        ),
        decisions=tuple(
            RenderDecisionDTO(
                decision_id=decision.id or 0,
                decision_type=decision.decision_type,
                action=decision.action,
                created_at=format_timestamp(decision.created_at),
                asset_role=decision.asset_role,
                details_json=decision.details_json,
            )
            for decision in decisions
        ),
    )
