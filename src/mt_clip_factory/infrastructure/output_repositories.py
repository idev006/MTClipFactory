from __future__ import annotations

from sqlalchemy.orm import Session

from mt_clip_factory.domain.outputs import Output
from mt_clip_factory.infrastructure.models import OutputModel


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
