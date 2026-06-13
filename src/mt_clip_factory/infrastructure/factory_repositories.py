from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.enums import RecipeStatus
from mt_clip_factory.domain.recipes import Recipe, RecipeItem, RecipeSummary
from mt_clip_factory.infrastructure.models import AssetModel, ProductModel, RecipeItemModel, RecipeModel


class SqlAlchemyRecipeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, recipe: Recipe) -> Recipe:
        model = RecipeModel(
            product_id=recipe.product_id,
            recipe_code=recipe.recipe_code,
            target_platform=recipe.target_platform,
            target_ratio=recipe.target_ratio,
            duration_sec=recipe.duration_sec,
            mood=recipe.mood,
            script_angle=recipe.script_angle,
            target_audience=recipe.target_audience,
            hook_text=recipe.hook_text,
            cta_text=recipe.cta_text,
            recipe_score=recipe.recipe_score,
            duplicate_risk=recipe.duplicate_risk,
            status=recipe.status.value,
            decision_actor=recipe.decision_actor,
            decision_at=recipe.decision_at,
            decision_reason=recipe.decision_reason,
            created_at=recipe.created_at,
        )
        self._session.add(model)
        self._session.flush()
        recipe.id = model.id
        return recipe

    def get_by_id(self, recipe_id: int) -> Recipe | None:
        model = self._session.get(RecipeModel, recipe_id)
        if model is None:
            return None
        return self._to_entity(model)

    def get_by_code(self, recipe_code: str) -> Recipe | None:
        statement = select(RecipeModel).where(RecipeModel.recipe_code == recipe_code)
        model = self._session.execute(statement).scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    def update(self, recipe: Recipe) -> Recipe:
        if recipe.id is None:
            raise ValueError("Recipe id is required for update.")
        model = self._session.get(RecipeModel, recipe.id)
        if model is None:
            raise ValueError(f"Unknown recipe id: {recipe.id}")
        model.recipe_code = recipe.recipe_code
        model.target_platform = recipe.target_platform
        model.target_ratio = recipe.target_ratio
        model.duration_sec = recipe.duration_sec
        model.mood = recipe.mood
        model.script_angle = recipe.script_angle
        model.target_audience = recipe.target_audience
        model.hook_text = recipe.hook_text
        model.cta_text = recipe.cta_text
        model.recipe_score = recipe.recipe_score
        model.duplicate_risk = recipe.duplicate_risk
        model.status = recipe.status.value
        model.decision_actor = recipe.decision_actor
        model.decision_at = recipe.decision_at
        model.decision_reason = recipe.decision_reason
        self._session.flush()
        return recipe

    def list_summaries(
        self,
        *,
        product_id: int | None = None,
        status: str | None = None,
    ) -> Sequence[RecipeSummary]:
        statement = (
            select(
                RecipeModel.id,
                RecipeModel.product_id,
                ProductModel.product_code,
                RecipeModel.recipe_code,
                RecipeModel.target_platform,
                RecipeModel.target_ratio,
                RecipeModel.recipe_score,
                RecipeModel.duplicate_risk,
                RecipeModel.status,
                RecipeModel.decision_actor,
                RecipeModel.decision_at,
                func.count(RecipeItemModel.id).label("item_count"),
            )
            .join(ProductModel, ProductModel.id == RecipeModel.product_id)
            .outerjoin(RecipeItemModel, RecipeItemModel.recipe_id == RecipeModel.id)
            .group_by(
                RecipeModel.id,
                RecipeModel.product_id,
                ProductModel.product_code,
                RecipeModel.recipe_code,
                RecipeModel.target_platform,
                RecipeModel.target_ratio,
                RecipeModel.recipe_score,
                RecipeModel.duplicate_risk,
                RecipeModel.status,
                RecipeModel.decision_actor,
                RecipeModel.decision_at,
            )
            .order_by(RecipeModel.created_at.desc(), RecipeModel.id.desc())
        )
        if product_id is not None:
            statement = statement.where(RecipeModel.product_id == product_id)
        if status is not None:
            statement = statement.where(RecipeModel.status == status)
        rows = self._session.execute(statement).all()
        return [
            RecipeSummary(
                recipe_id=row.id,
                product_id=row.product_id,
                product_code=row.product_code,
                recipe_code=row.recipe_code,
                target_platform=row.target_platform,
                target_ratio=row.target_ratio,
                recipe_score=row.recipe_score,
                duplicate_risk=row.duplicate_risk,
                status=RecipeStatus(row.status),
                decision_actor=row.decision_actor,
                decision_at=row.decision_at,
                item_count=row.item_count,
            )
            for row in rows
        ]

    def add_item(self, recipe_id: int, asset_id: int, role: str) -> RecipeItem:
        model = RecipeItemModel(recipe_id=recipe_id, asset_id=asset_id, role=role)
        self._session.add(model)
        self._session.flush()
        return RecipeItem(recipe_id=recipe_id, asset_id=asset_id, role=role, id=model.id)

    def update_item_asset(self, recipe_item_id: int, asset_id: int) -> RecipeItem:
        model = self._session.get(RecipeItemModel, recipe_item_id)
        if model is None:
            raise ValueError(f"Unknown recipe item id: {recipe_item_id}")
        model.asset_id = asset_id
        self._session.flush()
        return RecipeItem(
            id=model.id,
            recipe_id=model.recipe_id,
            asset_id=model.asset_id,
            role=model.role,
        )

    def list_items(self, recipe_id: int) -> Sequence[RecipeItem]:
        statement = (
            select(
                RecipeItemModel.id,
                RecipeItemModel.recipe_id,
                RecipeItemModel.asset_id,
                RecipeItemModel.role,
                AssetModel.asset_code,
                AssetModel.asset_type,
            )
            .join(AssetModel, AssetModel.id == RecipeItemModel.asset_id)
            .where(RecipeItemModel.recipe_id == recipe_id)
            .order_by(RecipeItemModel.id.asc())
        )
        rows = self._session.execute(statement).all()
        return [
            RecipeItem(
                id=row.id,
                recipe_id=row.recipe_id,
                asset_id=row.asset_id,
                role=row.role,
                asset_code=row.asset_code,
                asset_type=row.asset_type,
            )
            for row in rows
        ]

    def _to_entity(self, model: RecipeModel) -> Recipe:
        return Recipe(
            id=model.id,
            product_id=model.product_id,
            recipe_code=model.recipe_code,
            target_platform=model.target_platform,
            target_ratio=model.target_ratio,
            duration_sec=model.duration_sec,
            mood=model.mood,
            script_angle=model.script_angle,
            target_audience=model.target_audience,
            hook_text=model.hook_text,
            cta_text=model.cta_text,
            recipe_score=model.recipe_score,
            duplicate_risk=model.duplicate_risk,
            status=RecipeStatus(model.status),
            decision_actor=model.decision_actor,
            decision_at=model.decision_at,
            decision_reason=model.decision_reason,
            created_at=model.created_at,
        )
