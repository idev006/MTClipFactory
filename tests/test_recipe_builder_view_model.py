from __future__ import annotations

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.dto import RecipeDetailsDTO, RecipeItemDTO, RecipeSummaryDTO
from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.presentation.factory.recipe_builder import RecipeBuilderViewModel


class FakeAssetIntakeService:
    def list_assets(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[AssetSummaryDTO]:
        return [
            AssetSummaryDTO(
                asset_id=1,
                product_id=1,
                product_code="honey",
                asset_code="hero_asset",
                asset_type="background_video",
                file_name="hero.mp4",
                status="ready",
                ratio="16:9",
                duration_sec=3.0,
                file_size_mb=0.001,
                tag_labels=(),
                thumbnail_path=None,
                proxy_path=None,
            )
        ]


class FakeVideoAssemblyFactoryService:
    def __init__(self) -> None:
        self.recipes: list[RecipeSummaryDTO] = []
        self.items: dict[int, list[RecipeItemDTO]] = {}

    def create_recipe(self, command) -> int:
        recipe_id = len(self.recipes) + 1
        summary = RecipeSummaryDTO(
            recipe_id=recipe_id,
            product_id=command.product_id,
            product_code="honey",
            recipe_code=command.recipe_code.strip().lower().replace(" ", "_"),
            target_platform=command.target_platform,
            target_ratio=command.target_ratio,
            status="candidate",
            item_count=0,
        )
        self.recipes.append(summary)
        self.items[recipe_id] = []
        return recipe_id

    def list_recipes(self, *, product_id: int | None = None, status: str | None = None) -> list[RecipeSummaryDTO]:
        return list(self.recipes)

    def get_recipe(self, recipe_id: int) -> RecipeDetailsDTO:
        recipe = next(recipe for recipe in self.recipes if recipe.recipe_id == recipe_id)
        return RecipeDetailsDTO(
            recipe_id=recipe.recipe_id,
            product_id=recipe.product_id,
            recipe_code=recipe.recipe_code,
            target_platform=recipe.target_platform,
            target_ratio=recipe.target_ratio,
            duration_sec=None,
            mood=None,
            script_angle=None,
            target_audience=None,
            hook_text=None,
            cta_text=None,
            status=recipe.status,
            items=tuple(self.items[recipe_id]),
        )

    def assign_asset_to_recipe(self, command) -> int:
        item_id = len(self.items[command.recipe_id]) + 1
        self.items[command.recipe_id].append(
            RecipeItemDTO(
                recipe_item_id=item_id,
                asset_id=command.asset_id,
                asset_code="hero_asset",
                asset_type="background_video",
                role=command.role.strip().lower(),
            )
        )
        recipe = next(recipe for recipe in self.recipes if recipe.recipe_id == command.recipe_id)
        self.recipes[self.recipes.index(recipe)] = RecipeSummaryDTO(
            recipe_id=recipe.recipe_id,
            product_id=recipe.product_id,
            product_code=recipe.product_code,
            recipe_code=recipe.recipe_code,
            target_platform=recipe.target_platform,
            target_ratio=recipe.target_ratio,
            status=recipe.status,
            item_count=len(self.items[command.recipe_id]),
        )
        return item_id

    def enqueue_preview_job(self, recipe_id: int) -> int:
        return recipe_id

    def run_preview_job(self, job_id: int) -> None:
        return None


def test_recipe_builder_view_model_loads_products_assets_and_recipes(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    view_model = RecipeBuilderViewModel(
        product_service=product_service,
        asset_intake_service=FakeAssetIntakeService(),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
    )

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.products) == 1
    assert len(view_model.assets) == 1
    assert view_model.recipes == []


def test_recipe_builder_view_model_creates_recipe(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    factory_service = FakeVideoAssemblyFactoryService()
    view_model = RecipeBuilderViewModel(
        product_service=product_service,
        asset_intake_service=FakeAssetIntakeService(),
        video_assembly_factory_service=factory_service,
    )

    recipe_id = view_model.create_recipe(product_id=1, recipe_code="Honey Launch", target_platform="tiktok")

    assert recipe_id == 1
    assert view_model.status == "ready"
    assert len(view_model.recipes) == 1
    assert "Created recipe #1" in view_model.feedback


def test_recipe_builder_view_model_assigns_asset(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    factory_service = FakeVideoAssemblyFactoryService()
    view_model = RecipeBuilderViewModel(
        product_service=product_service,
        asset_intake_service=FakeAssetIntakeService(),
        video_assembly_factory_service=factory_service,
    )
    view_model.create_recipe(product_id=1, recipe_code="Honey Launch")

    item_id = view_model.assign_asset_to_recipe(recipe_id=1, asset_id=1, role="hero")

    assert item_id == 1
    assert view_model.status == "ready"
    assert len(view_model.recipe_items) == 1
    assert view_model.recipe_items[0].role == "hero"


def test_recipe_builder_view_model_builds_preview(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    factory_service = FakeVideoAssemblyFactoryService()
    view_model = RecipeBuilderViewModel(
        product_service=product_service,
        asset_intake_service=FakeAssetIntakeService(),
        video_assembly_factory_service=factory_service,
    )
    view_model.create_recipe(product_id=1, recipe_code="Honey Launch")

    job_id = view_model.queue_preview(1)

    assert job_id == 1
    assert view_model.status == "ready"
    assert "Built preview output for recipe #1" in view_model.feedback
