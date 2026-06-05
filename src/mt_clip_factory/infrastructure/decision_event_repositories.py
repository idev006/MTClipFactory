from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.decision_events import DecisionEvent
from mt_clip_factory.infrastructure.models import DecisionEventModel, OutputModel


class SqlAlchemyDecisionEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: DecisionEvent) -> DecisionEvent:
        model = DecisionEventModel(
            recipe_id=event.recipe_id,
            output_id=event.output_id,
            event_type=event.event_type,
            actor=event.actor,
            reason=event.reason,
            created_at=event.created_at,
        )
        self._session.add(model)
        self._session.flush()
        event.id = model.id
        return event

    def list_by_recipe(self, recipe_id: int) -> Sequence[DecisionEvent]:
        statement = (
            select(
                DecisionEventModel.id,
                DecisionEventModel.recipe_id,
                DecisionEventModel.output_id,
                DecisionEventModel.event_type,
                DecisionEventModel.actor,
                DecisionEventModel.reason,
                DecisionEventModel.created_at,
                OutputModel.output_code,
            )
            .outerjoin(OutputModel, OutputModel.id == DecisionEventModel.output_id)
            .where(DecisionEventModel.recipe_id == recipe_id)
            .order_by(DecisionEventModel.created_at.desc(), DecisionEventModel.id.desc())
        )
        rows = self._session.execute(statement).all()
        return [
            DecisionEvent(
                id=row.id,
                recipe_id=row.recipe_id,
                output_id=row.output_id,
                output_code=row.output_code,
                event_type=row.event_type,
                actor=row.actor,
                reason=row.reason,
                created_at=row.created_at,
            )
            for row in rows
        ]
