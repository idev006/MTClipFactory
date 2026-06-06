from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from mt_clip_factory.domain.assets import Asset, AssetSummary
from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.domain.decision_events import DecisionEvent
from mt_clip_factory.domain.entities import Product, ProductSummary
from mt_clip_factory.domain.jobs import Job, JobSummary
from mt_clip_factory.domain.outputs import Output, OutputSummary
from mt_clip_factory.domain.recipes import Recipe, RecipeItem, RecipeSummary
from mt_clip_factory.domain.render_decisions import RenderDecision
from mt_clip_factory.domain.tags import Tag, TagSummary


class ProductRepository(Protocol):
    def add(self, product: Product) -> Product:
        ...

    def get_by_id(self, product_id: int) -> Product | None:
        ...

    def get_by_code(self, product_code: str) -> Product | None:
        ...

    def update(self, product: Product) -> Product:
        ...

    def delete(self, product_id: int) -> None:
        ...

    def has_assets(self, product_id: int) -> bool:
        ...

    def list_summaries(self) -> Sequence[ProductSummary]:
        ...


class AssetRepository(Protocol):
    def add(self, asset: Asset) -> Asset:
        ...

    def get_by_id(self, asset_id: int) -> Asset | None:
        ...

    def get_by_code(self, asset_code: str) -> Asset | None:
        ...

    def update(self, asset: Asset) -> Asset:
        ...

    def list_summaries(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[AssetSummary]:
        ...

    def assign_tag(self, asset_id: int, tag_id: int) -> None:
        ...

    def list_tag_ids(self, asset_id: int) -> Sequence[int]:
        ...


class TagRepository(Protocol):
    def add(self, tag: Tag) -> Tag:
        ...

    def get_by_id(self, tag_id: int) -> Tag | None:
        ...

    def get_by_name_and_group(self, tag_name: str, tag_group: str) -> Tag | None:
        ...

    def list_summaries(self, tag_group: str | None = None) -> Sequence[TagSummary]:
        ...


class JobRepository(Protocol):
    def add(self, job: Job) -> Job:
        ...

    def get_by_id(self, job_id: int) -> Job | None:
        ...

    def list_summaries(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
    ) -> Sequence[JobSummary]:
        ...

    def update(self, job: Job) -> Job:
        ...


class RecipeRepository(Protocol):
    def add(self, recipe: Recipe) -> Recipe:
        ...

    def get_by_id(self, recipe_id: int) -> Recipe | None:
        ...

    def get_by_code(self, recipe_code: str) -> Recipe | None:
        ...

    def update(self, recipe: Recipe) -> Recipe:
        ...

    def list_summaries(
        self,
        *,
        product_id: int | None = None,
        status: str | None = None,
    ) -> Sequence[RecipeSummary]:
        ...

    def add_item(self, recipe_id: int, asset_id: int, role: str) -> RecipeItem:
        ...

    def list_items(self, recipe_id: int) -> Sequence[RecipeItem]:
        ...


class OutputRepository(Protocol):
    def add(self, output: Output) -> Output:
        ...

    def get_by_id(self, output_id: int) -> Output | None:
        ...

    def update(self, output: Output) -> Output:
        ...

    def list_summaries(
        self,
        *,
        recipe_id: int | None = None,
        approved: bool | None = None,
    ) -> Sequence[OutputSummary]:
        ...


class DecisionEventRepository(Protocol):
    def add(self, event: DecisionEvent) -> DecisionEvent:
        ...

    def list_by_recipe(self, recipe_id: int) -> Sequence[DecisionEvent]:
        ...


class CompositionPlanRepository(Protocol):
    def get_by_recipe(self, recipe_id: int) -> CompositionPlan | None:
        ...

    def upsert(self, plan: CompositionPlan) -> CompositionPlan:
        ...


class RenderDecisionRepository(Protocol):
    def replace_for_plan(self, composition_plan_id: int, decisions: Sequence[RenderDecision]) -> None:
        ...

    def list_by_plan(self, composition_plan_id: int) -> Sequence[RenderDecision]:
        ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], Protocol):
    products: ProductRepository
    assets: AssetRepository
    tags: TagRepository
    jobs: JobRepository
    recipes: RecipeRepository
    outputs: OutputRepository
    decision_events: DecisionEventRepository
    composition_plans: CompositionPlanRepository
    render_decisions: RenderDecisionRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
