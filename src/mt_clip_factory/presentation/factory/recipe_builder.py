from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.dto import (
    AssignAssetToRecipeCommand,
    CreateRecipeCommand,
    OutputSummaryDTO,
    RecipeItemDTO,
    RecipeSummaryDTO,
)
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetIntakeService


class RecipeBuilderViewModel(QObject):
    products_changed = Signal()
    assets_changed = Signal()
    recipes_changed = Signal()
    recipe_items_changed = Signal()
    outputs_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(
        self,
        product_service: ProductApplicationService,
        asset_intake_service: AssetIntakeService,
        video_assembly_factory_service: VideoAssemblyFactoryService,
    ) -> None:
        super().__init__()
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._video_assembly_factory_service = video_assembly_factory_service
        self._products = []
        self._assets: list[AssetSummaryDTO] = []
        self._recipes: list[RecipeSummaryDTO] = []
        self._recipe_items: list[RecipeItemDTO] = []
        self._outputs: list[OutputSummaryDTO] = []
        self._status = "idle"
        self._feedback = ""
        self._selected_recipe_id: int | None = None

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    def _get_feedback(self) -> str:
        return self._feedback

    def _set_feedback(self, value: str) -> None:
        if self._feedback == value:
            return
        self._feedback = value
        self.feedback_changed.emit()

    status = Property(str, _get_status, notify=status_changed)
    feedback = Property(str, _get_feedback, notify=feedback_changed)

    @property
    def products(self):
        return list(self._products)

    @property
    def assets(self) -> list[AssetSummaryDTO]:
        return list(self._assets)

    @property
    def recipes(self) -> list[RecipeSummaryDTO]:
        return list(self._recipes)

    @property
    def recipe_items(self) -> list[RecipeItemDTO]:
        return list(self._recipe_items)

    @property
    def outputs(self) -> list[OutputSummaryDTO]:
        return list(self._outputs)

    def load(self) -> None:
        self._set_status("loading")
        self._products = self._product_service.list_products()
        self._assets = self._asset_intake_service.list_assets(status="ready")
        self._recipes = self._video_assembly_factory_service.list_recipes()
        if self._selected_recipe_id is not None:
            self._load_selected_recipe_state(self._selected_recipe_id)
        else:
            self._recipe_items = []
            self._outputs = []
        self.products_changed.emit()
        self.assets_changed.emit()
        self.recipes_changed.emit()
        self.recipe_items_changed.emit()
        self.outputs_changed.emit()
        self._set_status("ready")

    def create_recipe(
        self,
        *,
        product_id: int,
        recipe_code: str,
        target_platform: str | None = None,
        target_ratio: str | None = None,
        duration_sec: float | None = None,
        mood: str | None = None,
        script_angle: str | None = None,
        target_audience: str | None = None,
        hook_text: str | None = None,
        cta_text: str | None = None,
    ) -> int:
        self._set_status("submitting")
        try:
            recipe_id = self._video_assembly_factory_service.create_recipe(
                CreateRecipeCommand(
                    product_id=product_id,
                    recipe_code=recipe_code,
                    target_platform=target_platform,
                    target_ratio=target_ratio,
                    duration_sec=duration_sec,
                    mood=mood,
                    script_angle=script_angle,
                    target_audience=target_audience,
                    hook_text=hook_text,
                    cta_text=cta_text,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Created recipe #{recipe_id}")
        self.load()
        return recipe_id

    def select_recipe(self, recipe_id: int | None) -> None:
        self._selected_recipe_id = recipe_id
        self._load_selected_recipe_state(recipe_id)
        self.recipe_items_changed.emit()
        self.outputs_changed.emit()

    def assign_asset_to_recipe(self, *, recipe_id: int, asset_id: int, role: str) -> int:
        self._set_status("submitting")
        try:
            recipe_item_id = self._video_assembly_factory_service.assign_asset_to_recipe(
                AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role=role)
            )
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Attached asset #{asset_id} to recipe #{recipe_id}")
        self.load()
        return recipe_item_id

    def queue_preview(self, recipe_id: int) -> int:
        self._set_status("processing")
        try:
            job_id = self._video_assembly_factory_service.enqueue_preview_job(recipe_id)
            self._video_assembly_factory_service.run_preview_job(job_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Built preview output for recipe #{recipe_id}")
        self.load()
        return job_id

    def approve_output(self, output_id: int) -> None:
        self._set_status("submitting")
        try:
            self._video_assembly_factory_service.approve_output(output_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Approved output #{output_id}")
        self.load()

    def approve_recipe(self, recipe_id: int) -> None:
        self._set_status("submitting")
        try:
            self._video_assembly_factory_service.approve_recipe(recipe_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Approved recipe #{recipe_id}")
        self.load()

    def reject_recipe(self, recipe_id: int) -> None:
        self._set_status("submitting")
        try:
            self._video_assembly_factory_service.reject_recipe(recipe_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Rejected recipe #{recipe_id}")
        self.load()

    def queue_final_render(self, recipe_id: int) -> int:
        self._set_status("processing")
        try:
            job_id = self._video_assembly_factory_service.enqueue_final_render_job(recipe_id)
            self._video_assembly_factory_service.run_final_render_job(job_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._selected_recipe_id = recipe_id
        self._set_feedback(f"Built final render for recipe #{recipe_id}")
        self.load()
        return job_id

    def _load_selected_recipe_state(self, recipe_id: int | None) -> None:
        if recipe_id is None:
            self._recipe_items = []
            self._outputs = []
            return
        recipe = self._video_assembly_factory_service.get_recipe(recipe_id)
        self._recipe_items = list(recipe.items)
        self._outputs = self._video_assembly_factory_service.list_outputs(recipe_id=recipe_id)
