from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.orm import Session

from mt_clip_factory.infrastructure.composition_repositories import (
    SqlAlchemyCompositionPlanRepository,
    SqlAlchemyRenderDecisionRepository,
)
from mt_clip_factory.infrastructure.decision_event_repositories import SqlAlchemyDecisionEventRepository
from mt_clip_factory.infrastructure.factory_repositories import SqlAlchemyRecipeRepository
from mt_clip_factory.infrastructure.job_repositories import SqlAlchemyJobRepository
from mt_clip_factory.infrastructure.output_repositories import SqlAlchemyOutputRepository
from mt_clip_factory.infrastructure.repositories import (
    SqlAlchemyAssetRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyTagRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        product_repository_type: type[SqlAlchemyProductRepository] = SqlAlchemyProductRepository,
        asset_repository_type: type[SqlAlchemyAssetRepository] = SqlAlchemyAssetRepository,
        tag_repository_type: type[SqlAlchemyTagRepository] = SqlAlchemyTagRepository,
        job_repository_type: type[SqlAlchemyJobRepository] = SqlAlchemyJobRepository,
        recipe_repository_type: type[SqlAlchemyRecipeRepository] = SqlAlchemyRecipeRepository,
        output_repository_type: type[SqlAlchemyOutputRepository] = SqlAlchemyOutputRepository,
        decision_event_repository_type: type[SqlAlchemyDecisionEventRepository] = SqlAlchemyDecisionEventRepository,
        composition_plan_repository_type: type[SqlAlchemyCompositionPlanRepository] = SqlAlchemyCompositionPlanRepository,
        render_decision_repository_type: type[SqlAlchemyRenderDecisionRepository] = SqlAlchemyRenderDecisionRepository,
    ) -> None:
        self._session_factory = session_factory
        self._product_repository_type = product_repository_type
        self._asset_repository_type = asset_repository_type
        self._tag_repository_type = tag_repository_type
        self._job_repository_type = job_repository_type
        self._recipe_repository_type = recipe_repository_type
        self._output_repository_type = output_repository_type
        self._decision_event_repository_type = decision_event_repository_type
        self._composition_plan_repository_type = composition_plan_repository_type
        self._render_decision_repository_type = render_decision_repository_type
        self.session: Session | None = None
        self.products: SqlAlchemyProductRepository
        self.assets: SqlAlchemyAssetRepository
        self.tags: SqlAlchemyTagRepository
        self.jobs: SqlAlchemyJobRepository
        self.recipes: SqlAlchemyRecipeRepository
        self.outputs: SqlAlchemyOutputRepository
        self.decision_events: SqlAlchemyDecisionEventRepository
        self.composition_plans: SqlAlchemyCompositionPlanRepository
        self.render_decisions: SqlAlchemyRenderDecisionRepository

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.products = self._product_repository_type(self.session)
        self.assets = self._asset_repository_type(self.session)
        self.tags = self._tag_repository_type(self.session)
        self.jobs = self._job_repository_type(self.session)
        self.recipes = self._recipe_repository_type(self.session)
        self.outputs = self._output_repository_type(self.session)
        self.decision_events = self._decision_event_repository_type(self.session)
        self.composition_plans = self._composition_plan_repository_type(self.session)
        self.render_decisions = self._render_decision_repository_type(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        if exc is not None:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.rollback()
