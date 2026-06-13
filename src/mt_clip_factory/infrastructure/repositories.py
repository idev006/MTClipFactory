from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.assets import Asset, AssetJobReference, AssetRecipeReference, AssetSummary
from mt_clip_factory.domain.entities import Product, ProductSummary
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.tags import Tag, TagSummary
from mt_clip_factory.infrastructure.models import (
    AssetModel,
    AssetTagModel,
    JobModel,
    OutputModel,
    ProductModel,
    RecipeItemModel,
    RecipeModel,
    TagModel,
)


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

    def get_by_id(self, product_id: int) -> Product | None:
        model = self._session.get(ProductModel, product_id)
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

    def update(self, product: Product) -> Product:
        if product.id is None:
            raise ValueError("Product id is required for update.")
        model = self._session.get(ProductModel, product.id)
        if model is None:
            raise ValueError(f"Unknown product id: {product.id}")

        model.product_code = product.product_code
        model.product_name = product.product_name
        model.category = product.category
        model.brand_name = product.brand_name
        model.description = product.description
        model.default_platform = product.default_platform
        self._session.flush()
        return product

    def delete(self, product_id: int) -> None:
        model = self._session.get(ProductModel, product_id)
        if model is None:
            return
        self._session.delete(model)
        self._session.flush()

    def has_assets(self, product_id: int) -> bool:
        statement = select(func.count(AssetModel.id)).where(AssetModel.product_id == product_id)
        asset_count = self._session.execute(statement).scalar_one()
        return asset_count > 0

    def list_summaries(self) -> Sequence[ProductSummary]:
        statement = (
            select(
                ProductModel.id,
                ProductModel.product_code,
                ProductModel.product_name,
                ProductModel.category,
                ProductModel.brand_name,
                ProductModel.default_platform,
                func.count(func.distinct(AssetModel.id)).label("asset_count"),
                func.count(func.distinct(RecipeModel.id)).label("recipe_count"),
                func.count(func.distinct(OutputModel.id)).label("output_count"),
            )
            .outerjoin(AssetModel, AssetModel.product_id == ProductModel.id)
            .outerjoin(RecipeModel, RecipeModel.product_id == ProductModel.id)
            .outerjoin(OutputModel, OutputModel.recipe_id == RecipeModel.id)
            .group_by(
                ProductModel.id,
                ProductModel.product_code,
                ProductModel.product_name,
                ProductModel.category,
                ProductModel.brand_name,
                ProductModel.default_platform,
            )
            .order_by(ProductModel.product_name.asc())
        )
        rows = self._session.execute(statement).all()
        return [
            ProductSummary(
                product_id=row.id,
                product_code=row.product_code,
                product_name=row.product_name,
                category=row.category,
                brand_name=row.brand_name,
                default_platform=row.default_platform,
                asset_count=row.asset_count,
                recipe_count=row.recipe_count,
                output_count=row.output_count,
            )
            for row in rows
        ]


class SqlAlchemyAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, asset: Asset) -> Asset:
        model = AssetModel(
            product_id=asset.product_id,
            asset_code=asset.asset_code,
            asset_type=asset.asset_type.value,
            file_path=asset.file_path,
            file_name=asset.file_name,
            duration_sec=asset.duration_sec,
            width=asset.width,
            height=asset.height,
            fps=asset.fps,
            ratio=asset.ratio,
            file_size_mb=asset.file_size_mb,
            codec=asset.codec,
            has_audio=asset.has_audio,
            thumbnail_path=asset.thumbnail_path,
            proxy_path=asset.proxy_path,
            alpha_path=asset.alpha_path,
            rgba_cache_path=asset.rgba_cache_path,
            quality_score=asset.quality_score,
            status=asset.status,
            created_at=asset.created_at,
        )
        self._session.add(model)
        self._session.flush()
        asset.id = model.id
        return asset

    def get_by_id(self, asset_id: int) -> Asset | None:
        model = self._session.get(AssetModel, asset_id)
        if model is None:
            return None
        return self._to_entity(model)

    def get_by_code(self, asset_code: str) -> Asset | None:
        statement: Select[tuple[AssetModel]] = select(AssetModel).where(AssetModel.asset_code == asset_code)
        model = self._session.execute(statement).scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    def update(self, asset: Asset) -> Asset:
        if asset.id is None:
            raise ValueError("Asset id is required for update.")
        model = self._session.get(AssetModel, asset.id)
        if model is None:
            raise ValueError(f"Unknown asset id: {asset.id}")

        model.product_id = asset.product_id
        model.asset_code = asset.asset_code
        model.asset_type = asset.asset_type.value
        model.file_path = asset.file_path
        model.file_name = asset.file_name
        model.duration_sec = asset.duration_sec
        model.width = asset.width
        model.height = asset.height
        model.fps = asset.fps
        model.ratio = asset.ratio
        model.file_size_mb = asset.file_size_mb
        model.codec = asset.codec
        model.has_audio = asset.has_audio
        model.thumbnail_path = asset.thumbnail_path
        model.proxy_path = asset.proxy_path
        model.alpha_path = asset.alpha_path
        model.rgba_cache_path = asset.rgba_cache_path
        model.quality_score = asset.quality_score
        model.status = asset.status
        self._session.flush()
        return asset

    def delete(self, asset_id: int) -> None:
        model = self._session.get(AssetModel, asset_id)
        if model is None:
            return
        self._session.execute(delete(AssetTagModel).where(AssetTagModel.asset_id == asset_id))
        self._session.delete(model)
        self._session.flush()

    def has_recipe_item_references(self, asset_id: int) -> bool:
        statement = select(func.count(RecipeItemModel.id)).where(RecipeItemModel.asset_id == asset_id)
        return self._session.execute(statement).scalar_one() > 0

    def has_job_references(self, asset_id: int) -> bool:
        statement = select(func.count(JobModel.id)).where(JobModel.asset_id == asset_id)
        return self._session.execute(statement).scalar_one() > 0

    def list_recipe_references(self, asset_id: int) -> Sequence[AssetRecipeReference]:
        statement = (
            select(
                RecipeModel.id,
                RecipeModel.recipe_code,
                RecipeModel.status,
                func.count(func.distinct(OutputModel.id)).label("output_count"),
            )
            .join(RecipeItemModel, RecipeItemModel.recipe_id == RecipeModel.id)
            .outerjoin(OutputModel, OutputModel.recipe_id == RecipeModel.id)
            .where(RecipeItemModel.asset_id == asset_id)
            .group_by(RecipeModel.id, RecipeModel.recipe_code, RecipeModel.status)
            .order_by(RecipeModel.id.asc())
        )
        rows = self._session.execute(statement).all()
        return [
            AssetRecipeReference(
                recipe_id=row.id,
                recipe_code=row.recipe_code,
                recipe_status=row.status,
                output_count=row.output_count,
            )
            for row in rows
        ]

    def list_job_references(self, asset_id: int) -> Sequence[AssetJobReference]:
        statement = (
            select(JobModel.id, JobModel.job_code, JobModel.job_type, JobModel.status)
            .where(JobModel.asset_id == asset_id)
            .order_by(JobModel.id.asc())
        )
        rows = self._session.execute(statement).all()
        return [
            AssetJobReference(
                job_id=row.id,
                job_code=row.job_code,
                job_type=row.job_type,
                job_status=row.status,
            )
            for row in rows
        ]

    def list_summaries(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[AssetSummary]:
        statement = (
            select(
                AssetModel.id,
                AssetModel.product_id,
                ProductModel.product_code,
                AssetModel.asset_code,
                AssetModel.asset_type,
                AssetModel.file_name,
                AssetModel.status,
                AssetModel.ratio,
                AssetModel.duration_sec,
                AssetModel.file_size_mb,
                AssetModel.thumbnail_path,
                AssetModel.proxy_path,
            )
            .join(ProductModel, ProductModel.id == AssetModel.product_id)
            .order_by(AssetModel.created_at.desc(), AssetModel.id.desc())
        )
        if product_id is not None:
            statement = statement.where(AssetModel.product_id == product_id)
        if asset_type is not None:
            statement = statement.where(AssetModel.asset_type == asset_type)
        if status is not None:
            statement = statement.where(AssetModel.status == status)

        rows = self._session.execute(statement).all()
        return [
            AssetSummary(
                asset_id=row.id,
                product_id=row.product_id,
                product_code=row.product_code,
                asset_code=row.asset_code,
                asset_type=AssetType(row.asset_type),
                file_name=row.file_name,
                status=row.status,
                ratio=row.ratio,
                duration_sec=row.duration_sec,
                file_size_mb=row.file_size_mb,
                tag_labels=self._load_tag_labels(row.id),
                thumbnail_path=row.thumbnail_path,
                proxy_path=row.proxy_path,
            )
            for row in rows
        ]

    def assign_tag(self, asset_id: int, tag_id: int) -> None:
        existing = self._session.get(AssetTagModel, {"asset_id": asset_id, "tag_id": tag_id})
        if existing is not None:
            return
        self._session.add(AssetTagModel(asset_id=asset_id, tag_id=tag_id))
        self._session.flush()

    def list_tag_ids(self, asset_id: int) -> Sequence[int]:
        statement = select(AssetTagModel.tag_id).where(AssetTagModel.asset_id == asset_id)
        return list(self._session.execute(statement).scalars())

    def _load_tag_labels(self, asset_id: int) -> tuple[str, ...]:
        statement = (
            select(TagModel.tag_group, TagModel.tag_name)
            .join(AssetTagModel, AssetTagModel.tag_id == TagModel.id)
            .where(AssetTagModel.asset_id == asset_id)
            .order_by(TagModel.tag_group.asc(), TagModel.tag_name.asc())
        )
        rows = self._session.execute(statement).all()
        return tuple(f"{row.tag_group}:{row.tag_name}" for row in rows)

    def _to_entity(self, model: AssetModel) -> Asset:
        return Asset(
            id=model.id,
            product_id=model.product_id,
            asset_code=model.asset_code,
            asset_type=AssetType(model.asset_type),
            file_path=model.file_path,
            file_name=model.file_name,
            duration_sec=model.duration_sec,
            width=model.width,
            height=model.height,
            fps=model.fps,
            ratio=model.ratio,
            file_size_mb=model.file_size_mb,
            codec=model.codec,
            has_audio=model.has_audio,
            thumbnail_path=model.thumbnail_path,
            proxy_path=model.proxy_path,
            alpha_path=model.alpha_path,
            rgba_cache_path=model.rgba_cache_path,
            quality_score=model.quality_score,
            status=model.status,
            created_at=model.created_at,
        )


class SqlAlchemyTagRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, tag: Tag) -> Tag:
        model = TagModel(
            tag_name=tag.tag_name,
            tag_group=tag.tag_group,
            description=tag.description,
        )
        self._session.add(model)
        self._session.flush()
        tag.id = model.id
        return tag

    def get_by_id(self, tag_id: int) -> Tag | None:
        model = self._session.get(TagModel, tag_id)
        if model is None:
            return None
        return Tag(
            id=model.id,
            tag_name=model.tag_name,
            tag_group=model.tag_group,
            description=model.description,
        )

    def get_by_name_and_group(self, tag_name: str, tag_group: str) -> Tag | None:
        statement: Select[tuple[TagModel]] = select(TagModel).where(
            TagModel.tag_name == tag_name,
            TagModel.tag_group == tag_group,
        )
        model = self._session.execute(statement).scalar_one_or_none()
        if model is None:
            return None
        return Tag(
            id=model.id,
            tag_name=model.tag_name,
            tag_group=model.tag_group,
            description=model.description,
        )

    def list_summaries(self, tag_group: str | None = None) -> Sequence[TagSummary]:
        statement = select(TagModel).order_by(TagModel.tag_group.asc(), TagModel.tag_name.asc())
        if tag_group is not None:
            statement = statement.where(TagModel.tag_group == tag_group)
        rows = self._session.execute(statement).scalars().all()
        return [
            TagSummary(
                tag_id=row.id,
                tag_name=row.tag_name,
                tag_group=row.tag_group,
                description=row.description,
            )
            for row in rows
        ]
