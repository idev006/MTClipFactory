from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.composition_plans import CompositionLayerAssignment, CompositionPlan
from mt_clip_factory.domain.render_decisions import RenderDecision
from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.infrastructure.models import CompositionPlanModel, RenderDecisionModel, TimelineSegmentModel


class SqlAlchemyCompositionPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_recipe(self, recipe_id: int) -> CompositionPlan | None:
        statement = select(CompositionPlanModel).where(CompositionPlanModel.recipe_id == recipe_id)
        model = self._session.execute(statement).scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    def upsert(self, plan: CompositionPlan) -> CompositionPlan:
        statement = select(CompositionPlanModel).where(CompositionPlanModel.recipe_id == plan.recipe_id)
        model = self._session.execute(statement).scalar_one_or_none()
        layer_assignments_json = json.dumps(
            [
                {
                    "layer_name": layer.layer_name,
                    "asset_ids": list(layer.asset_ids),
                    "asset_codes": list(layer.asset_codes),
                }
                for layer in plan.layer_assignments
            ],
            sort_keys=True,
        )
        if model is None:
            model = CompositionPlanModel(
                recipe_id=plan.recipe_id,
                duration_source=plan.duration_source,
                target_duration_sec=plan.target_duration_sec,
                resolved_duration_sec=plan.resolved_duration_sec,
                layer_assignments_json=layer_assignments_json,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            self._session.add(model)
        else:
            model.duration_source = plan.duration_source
            model.target_duration_sec = plan.target_duration_sec
            model.resolved_duration_sec = plan.resolved_duration_sec
            model.layer_assignments_json = layer_assignments_json
            model.updated_at = plan.updated_at
        self._session.flush()
        plan.id = model.id
        return plan

    def _to_entity(self, model: CompositionPlanModel) -> CompositionPlan:
        payload = json.loads(model.layer_assignments_json)
        return CompositionPlan(
            id=model.id,
            recipe_id=model.recipe_id,
            duration_source=model.duration_source,
            target_duration_sec=model.target_duration_sec,
            resolved_duration_sec=model.resolved_duration_sec,
            layer_assignments=tuple(
                CompositionLayerAssignment(
                    layer_name=item["layer_name"],
                    asset_ids=tuple(item["asset_ids"]),
                    asset_codes=tuple(item["asset_codes"]),
                )
                for item in payload
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyRenderDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_plan(self, composition_plan_id: int, decisions: Sequence[RenderDecision]) -> None:
        self._session.execute(delete(RenderDecisionModel).where(RenderDecisionModel.composition_plan_id == composition_plan_id))
        for decision in decisions:
            model = RenderDecisionModel(
                composition_plan_id=composition_plan_id,
                recipe_id=decision.recipe_id,
                decision_type=decision.decision_type,
                asset_role=decision.asset_role,
                action=decision.action,
                details_json=decision.details_json,
                created_at=decision.created_at,
            )
            self._session.add(model)
        self._session.flush()

    def list_by_plan(self, composition_plan_id: int) -> Sequence[RenderDecision]:
        statement = (
            select(RenderDecisionModel)
            .where(RenderDecisionModel.composition_plan_id == composition_plan_id)
            .order_by(RenderDecisionModel.id.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [
            RenderDecision(
                id=model.id,
                composition_plan_id=model.composition_plan_id,
                recipe_id=model.recipe_id,
                decision_type=model.decision_type,
                asset_role=model.asset_role,
                action=model.action,
                details_json=model.details_json,
                created_at=model.created_at,
            )
            for model in models
        ]


class SqlAlchemyTimelineSegmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_plan(self, composition_plan_id: int, segments: Sequence[TimelineSegment]) -> None:
        self._session.execute(delete(TimelineSegmentModel).where(TimelineSegmentModel.composition_plan_id == composition_plan_id))
        for segment in segments:
            model = TimelineSegmentModel(
                composition_plan_id=composition_plan_id,
                recipe_id=segment.recipe_id,
                segment_type=segment.segment_type,
                sequence_index=segment.sequence_index,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                target_duration_sec=segment.target_duration_sec,
                message_text=segment.message_text,
                preferred_layers_json=json.dumps(list(segment.preferred_layers), sort_keys=True),
                text_rule=segment.text_rule,
                audio_policy=segment.audio_policy,
                created_at=segment.created_at,
            )
            self._session.add(model)
        self._session.flush()

    def list_by_plan(self, composition_plan_id: int) -> Sequence[TimelineSegment]:
        statement = (
            select(TimelineSegmentModel)
            .where(TimelineSegmentModel.composition_plan_id == composition_plan_id)
            .order_by(TimelineSegmentModel.sequence_index.asc())
        )
        models = self._session.execute(statement).scalars().all()
        return [
            TimelineSegment(
                id=model.id,
                composition_plan_id=model.composition_plan_id,
                recipe_id=model.recipe_id,
                segment_type=model.segment_type,
                sequence_index=model.sequence_index,
                start_sec=model.start_sec,
                end_sec=model.end_sec,
                target_duration_sec=model.target_duration_sec,
                message_text=model.message_text,
                preferred_layers=tuple(json.loads(model.preferred_layers_json)),
                text_rule=model.text_rule,
                audio_policy=model.audio_policy,
                created_at=model.created_at,
            )
            for model in models
        ]
