from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.entities import Product, ProductSummary
from mt_clip_factory.infrastructure.models import AssetModel, OutputModel, ProductModel, RecipeModel


class SqlAlchemyProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, product: Product) -> Product:
        model = ProductModel(
            product_code=product.product_code,
            product_name=product.product_name,
            category=product.category,
            brand_name=product.brand_name,
            description=product.description,
            default_platform=product.default_platform,
            created_at=product.created_at,
        )
        self._session.add(model)
        self._session.flush()
        product.id = model.id
        return product

    def get_by_code(self, product_code: str) -> Product | None:
        statement: Select[tuple[ProductModel]] = select(ProductModel).where(ProductModel.product_code == product_code)
        model = self._session.execute(statement).scalar_one_or_none()
        if model is None:
            return None

        return Product(
            id=model.id,
            product_code=model.product_code,
            product_name=model.product_name,
            category=model.category,
            brand_name=model.brand_name,
            description=model.description,
            default_platform=model.default_platform,
            created_at=model.created_at,
        )

    def list_summaries(self) -> Sequence[ProductSummary]:
        statement = (
            select(
                ProductModel.id,
                ProductModel.product_code,
                ProductModel.product_name,
                func.count(func.distinct(AssetModel.id)).label("asset_count"),
                func.count(func.distinct(RecipeModel.id)).label("recipe_count"),
                func.count(func.distinct(OutputModel.id)).label("output_count"),
            )
            .outerjoin(AssetModel, AssetModel.product_id == ProductModel.id)
            .outerjoin(RecipeModel, RecipeModel.product_id == ProductModel.id)
            .outerjoin(OutputModel, OutputModel.recipe_id == RecipeModel.id)
            .group_by(ProductModel.id, ProductModel.product_code, ProductModel.product_name)
            .order_by(ProductModel.product_name.asc())
        )
        rows = self._session.execute(statement).all()
        return [
            ProductSummary(
                product_id=row.id,
                product_code=row.product_code,
                product_name=row.product_name,
                asset_count=row.asset_count,
                recipe_count=row.recipe_count,
                output_count=row.output_count,
            )
            for row in rows
        ]

