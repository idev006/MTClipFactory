from __future__ import annotations

from collections.abc import Sequence

from mt_clip_factory.domain.production_orders import ProductionOrderStage
from mt_clip_factory.factory.production_order_detail_support import effective_stages, stage_detail_value

RISK_LEVEL_HIGH = "High"
RISK_LEVEL_MEDIUM = "Medium"
RISK_LEVEL_LOW = "Low"
RISK_LEVEL_UNAVAILABLE = "Unavailable"


def classify_near_duplicate_score(score: float | None) -> str:
    if score is None:
        return RISK_LEVEL_UNAVAILABLE
    if score >= 0.6:
        return RISK_LEVEL_HIGH
    if score >= 0.25:
        return RISK_LEVEL_MEDIUM
    return RISK_LEVEL_LOW


def max_materialize_risk_score(stages: Sequence[ProductionOrderStage]) -> float | None:
    risk_scores = [
        score
        for score in (
            _stage_near_duplicate_score(stage)
            for stage in effective_stages(stages)
            if stage.stage_name == "materialize" and stage.status.value == "succeeded"
        )
        if score is not None
    ]
    if not risk_scores:
        return None
    return max(risk_scores)


def max_render_duplicate_score(stages: Sequence[ProductionOrderStage]) -> float | None:
    risk_scores = [
        score
        for score in (
            _stage_render_duplicate_score(stage)
            for stage in effective_stages(stages)
            if stage.stage_name in {"preview", "review"} and stage.status.value in {"succeeded", "review_required"}
        )
        if score is not None
    ]
    if not risk_scores:
        return None
    return max(risk_scores)


def max_duplicate_truth_score(stages: Sequence[ProductionOrderStage]) -> float | None:
    candidates = [
        score
        for score in (
            max_materialize_risk_score(stages),
            max_render_duplicate_score(stages),
        )
        if score is not None
    ]
    if not candidates:
        return None
    return max(candidates)


def _stage_near_duplicate_score(stage: ProductionOrderStage) -> float | None:
    value = stage_detail_value(stage.detail_json, "near_duplicate_score")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stage_render_duplicate_score(stage: ProductionOrderStage) -> float | None:
    value = stage_detail_value(stage.detail_json, "duplicate_risk")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
