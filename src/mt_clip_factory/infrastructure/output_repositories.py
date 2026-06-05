from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.outputs import Output, OutputSummary
from mt_clip_factory.infrastructure.models import OutputModel, RecipeModel


class SqlAlchemyOutputRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, output: Output) -> Output:
        model = OutputModel(
            recipe_id=output.recipe_id,
            output_code=output.output_code,
            file_path=output.file_path,
            platform=output.platform,
            ratio=output.ratio,
            duration_sec=output.duration_sec,
            quality_score=output.quality_score,
            duplicate_risk=output.duplicate_risk,
            approved=output.approved,
            created_at=output.created_at,
        )
        self._session.add(model)
        self._session.flush()
        output.id = model.id
        return output

    def get_by_id(self, output_id: int) -> Output | None:
        model = self._session.get(OutputModel, output_id)
        if model is None:
            return None
        return self._to_entity(model)

    def update(self, output: Output) -> Output:
        if output.id is None:
            raise ValueError("Output id is required for update.")
        model = self._session.get(OutputModel, output.id)
        if model is None:
            raise ValueError(f"Unknown output id: {output.id}")
        model.file_path = output.file_path
        model.platform = output.platform
        model.ratio = output.ratio
        model.duration_sec = output.duration_sec
        model.quality_score = output.quality_score
        model.duplicate_risk = output.duplicate_risk
        model.approved = output.approved
        self._session.flush()
        return output

    def list_summaries(
        self,
        *,
        recipe_id: int | None = None,
        approved: bool | None = None,
    ) -> Sequence[OutputSummary]:
        statement = (
            select(
                OutputModel.id,
                OutputModel.recipe_id,
                RecipeModel.recipe_code,
                OutputModel.output_code,
                OutputModel.file_path,
                OutputModel.platform,
                OutputModel.ratio,
                OutputModel.approved,
                OutputModel.created_at,
            )
            .join(RecipeModel, RecipeModel.id == OutputModel.recipe_id)
            .order_by(OutputModel.created_at.desc(), OutputModel.id.desc())
        )
        if recipe_id is not None:
            statement = statement.where(OutputModel.recipe_id == recipe_id)
        if approved is not None:
            statement = statement.where(OutputModel.approved == approved)
        rows = self._session.execute(statement).all()
        return [
            OutputSummary(
                output_id=row.id,
                recipe_id=row.recipe_id,
                recipe_code=row.recipe_code,
                output_code=row.output_code,
                file_path=row.file_path,
                platform=row.platform,
                ratio=row.ratio,
                approved=row.approved,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def _to_entity(self, model: OutputModel) -> Output:
        return Output(
            id=model.id,
            recipe_id=model.recipe_id,
            output_code=model.output_code,
            file_path=model.file_path,
            platform=model.platform,
            ratio=model.ratio,
            duration_sec=model.duration_sec,
            quality_score=model.quality_score,
            duplicate_risk=model.duplicate_risk,
            approved=model.approved,
            created_at=model.created_at,
        )
