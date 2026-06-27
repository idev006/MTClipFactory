from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.domain.render_decisions import RenderDecision
from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.automation_policy import ProductAutomationFillPolicies
from mt_clip_factory.factory.composition_mapping import bind_render_decision, bind_timeline_segment
from mt_clip_factory.factory.composition_planning import build_default_composition


@dataclass(slots=True, frozen=True)
class PersistedComposition:
    plan: CompositionPlan
    segments: tuple[TimelineSegment, ...]
    decisions: tuple[RenderDecision, ...]


def persist_composition(
    uow,
    *,
    recipe: Recipe,
    items: Sequence[RecipeItem],
    assets: dict[int, Asset],
    fill_policies: ProductAutomationFillPolicies | None = None,
    segment_profile: str | None = None,
) -> PersistedComposition:
    planned = build_default_composition(
        recipe,
        list(items),
        assets,
        fill_policies=fill_policies,
        segment_profile=segment_profile,
    )
    plan = uow.composition_plans.upsert(planned.plan)
    if plan.id is None:
        raise RuntimeError("Composition plan identifier was not assigned.")
    segments = tuple(
        bind_timeline_segment(segment, composition_plan_id=plan.id)
        for segment in planned.segments
    )
    decisions = tuple(
        bind_render_decision(decision, composition_plan_id=plan.id)
        for decision in planned.decisions
    )
    uow.timeline_segments.replace_for_plan(plan.id, segments)
    uow.render_decisions.replace_for_plan(plan.id, decisions)
    return PersistedComposition(plan=plan, segments=segments, decisions=decisions)
