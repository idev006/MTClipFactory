from __future__ import annotations

from dataclasses import replace

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.artifact_dto import ArtifactJobSummaryDTO
from mt_clip_factory.library.dto import (
    AssetMediaPurgeReportDTO,
    AssetReferenceReportDTO,
    AssetReplacementAffectedRecipeDTO,
    AssetReplacementReportDTO,
    AssetSummaryDTO,
)
from mt_clip_factory.library.services import AssetSourceFileMissingError
from mt_clip_factory.presentation.library.asset_library import AssetLibraryViewModel


class FakeAssetIntakeService:
    def __init__(self) -> None:
        self.assets: list[AssetSummaryDTO] = []
        self.calls: list[tuple[int, str, str, str | None]] = []
        self.updated_assets: list[tuple[int, str]] = []
        self.deleted_asset_ids: list[int] = []
        self.retired_asset_ids: list[int] = []
        self.purged_asset_ids: list[int] = []
        self.replaced_pairs: list[tuple[int, int]] = []

    def register_asset(self, command) -> int:
        if "missing" in str(command.source_file_path):
            raise AssetSourceFileMissingError(str(command.source_file_path))
        self.calls.append(
            (command.product_id, command.asset_type, str(command.source_file_path), command.asset_code)
        )
        asset_id = len(self.assets) + 1
        self.assets.append(
            AssetSummaryDTO(
                asset_id=asset_id,
                product_id=command.product_id,
                product_code="honey",
                asset_code=command.asset_code or "auto_code",
                asset_type=command.asset_type,
                file_name="hero.mp4",
                status="ready",
                ratio=None,
                duration_sec=None,
                file_size_mb=0.001,
                tag_labels=(),
                thumbnail_path=None,
                proxy_path=None,
            )
        )
        return asset_id

    def list_assets(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[AssetSummaryDTO]:
        return list(self.assets)

    def update_asset(self, command) -> int:
        self.updated_assets.append((command.asset_id, command.asset_code))
        for index, asset in enumerate(self.assets):
            if asset.asset_id != command.asset_id:
                continue
            self.assets[index] = replace(asset, asset_code=command.asset_code)
            return command.asset_id
        raise ValueError(str(command.asset_id))

    def delete_asset(self, asset_id: int) -> None:
        self.deleted_asset_ids.append(asset_id)
        self.assets = [asset for asset in self.assets if asset.asset_id != asset_id]

    def retire_asset(self, asset_id: int) -> int:
        self.retired_asset_ids.append(asset_id)
        for index, asset in enumerate(self.assets):
            if asset.asset_id != asset_id:
                continue
            self.assets[index] = replace(asset, status="retired")
            return asset_id
        raise ValueError(str(asset_id))

    def purge_asset_media(self, asset_id: int) -> AssetMediaPurgeReportDTO:
        self.purged_asset_ids.append(asset_id)
        for index, asset in enumerate(self.assets):
            if asset.asset_id != asset_id:
                continue
            self.assets[index] = replace(asset, status="purged", thumbnail_path=None, proxy_path=None)
            return AssetMediaPurgeReportDTO(
                asset_id=asset_id,
                asset_code=asset.asset_code,
                purged_file_count=2,
                reclaimed_bytes=1024,
            )
        raise ValueError(str(asset_id))

    def describe_asset_references(self, asset_id: int) -> AssetReferenceReportDTO:
        for asset in self.assets:
            if asset.asset_id != asset_id:
                continue
            return AssetReferenceReportDTO(
                asset_id=asset_id,
                asset_code=asset.asset_code,
                asset_status=asset.status,
                recipe_references=(),
                job_references=(),
                can_delete=True,
                can_purge_media=asset.status == "retired",
            )
        raise ValueError(str(asset_id))

    def list_replacement_candidates(self, asset_id: int) -> list[AssetSummaryDTO]:
        return [asset for asset in self.assets if asset.asset_id != asset_id and asset.status == "ready"]

    def replace_asset_in_recipes(self, source_asset_id: int, replacement_asset_id: int) -> AssetReplacementReportDTO:
        self.replaced_pairs.append((source_asset_id, replacement_asset_id))
        source_asset = next(asset for asset in self.assets if asset.asset_id == source_asset_id)
        replacement_asset = next(asset for asset in self.assets if asset.asset_id == replacement_asset_id)
        return AssetReplacementReportDTO(
            source_asset_id=source_asset_id,
            source_asset_code=source_asset.asset_code,
            replacement_asset_id=replacement_asset_id,
            replacement_asset_code=replacement_asset.asset_code,
            replaced_item_count=2,
            affected_recipes=(
                AssetReplacementAffectedRecipeDTO(
                    recipe_id=11,
                    recipe_code="recipe_11",
                    previous_status="approved",
                    output_count=2,
                ),
            ),
        )


class FakeArtifactGenerationService:
    def __init__(self, asset_service: FakeAssetIntakeService) -> None:
        self._asset_service = asset_service
        self._jobs: dict[int, tuple[str, int]] = {}
        self.calls: list[tuple[str, int]] = []
        self._next_job_id = 1

    def enqueue_thumbnail_job(self, asset_id: int) -> int:
        return self._enqueue("thumbnail", asset_id)

    def enqueue_proxy_job(self, asset_id: int) -> int:
        return self._enqueue("proxy", asset_id)

    def run_job(self, job_id: int) -> None:
        job_type, asset_id = self._jobs[job_id]
        for index, asset in enumerate(self._asset_service.assets):
            if asset.asset_id != asset_id:
                continue
            if job_type == "thumbnail":
                self._asset_service.assets[index] = replace(
                    asset,
                    thumbnail_path=f"cache/thumbnails/{asset.asset_code}.jpg",
                )
            else:
                self._asset_service.assets[index] = replace(
                    asset,
                    proxy_path=f"cache/proxy/{asset.asset_code}.mp4",
                )
            break
        self.calls.append((job_type, asset_id))

    def list_jobs(self, *, status: str | None = None) -> list[ArtifactJobSummaryDTO]:
        return []

    def _enqueue(self, job_type: str, asset_id: int) -> int:
        job_id = self._next_job_id
        self._jobs[job_id] = (job_type, asset_id)
        self._next_job_id += 1
        return job_id


def test_asset_view_model_loads_products_and_assets(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.products) == 1
    assert view_model.assets == []


def test_asset_view_model_registers_asset_and_refreshes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )

    asset_id = view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    assert asset_id == 1
    assert view_model.status == "ready"
    assert "Registered asset #1" in view_model.feedback
    assert len(view_model.assets) == 1


def test_asset_view_model_surfaces_register_errors(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )

    with pytest.raises(FileNotFoundError):
        view_model.register_asset(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=str(tmp_path / "missing.mp4"),
            asset_code="hero_asset",
        )

    assert view_model.status == "error"
    assert "missing.mp4" in view_model.feedback


def test_asset_view_model_applies_filters(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )

    view_model.apply_filters(product_id=1, asset_type="background_video", status="ready")

    assert view_model.status == "ready"


def test_asset_view_model_generates_thumbnail_and_refreshes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    job_id = view_model.generate_thumbnail(1)

    assert job_id == 1
    assert view_model.status == "ready"
    assert "Generated thumbnail for asset #1" in view_model.feedback
    assert asset_service.assets[0].thumbnail_path is not None
    assert artifact_service.calls == [("thumbnail", 1)]


def test_asset_view_model_generates_proxy_and_refreshes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    job_id = view_model.generate_proxy(1)

    assert job_id == 1
    assert view_model.status == "ready"
    assert "Generated proxy for asset #1" in view_model.feedback
    assert asset_service.assets[0].proxy_path is not None
    assert artifact_service.calls == [("proxy", 1)]


def test_asset_view_model_updates_selected_asset(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    updated_asset_id = view_model.update_asset(asset_id=1, asset_code="hero_asset_v2")

    assert updated_asset_id == 1
    assert asset_service.updated_assets == [(1, "hero_asset_v2")]
    assert view_model.assets[0].asset_code == "hero_asset_v2"
    assert view_model.feedback == "Updated asset #1"


def test_asset_view_model_deletes_selected_asset(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    view_model.delete_asset(1)

    assert asset_service.deleted_asset_ids == [1]
    assert view_model.assets == []
    assert view_model.feedback == "Deleted asset #1"


def test_asset_view_model_retires_selected_asset(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    retired_asset_id = view_model.retire_asset(1)

    assert retired_asset_id == 1
    assert asset_service.retired_asset_ids == [1]
    assert view_model.assets[0].status == "retired"
    assert view_model.feedback == "Retired asset #1"


def test_asset_view_model_purges_media_and_refreshes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )
    view_model.retire_asset(1)

    report = view_model.purge_asset_media(1)

    assert report.asset_id == 1
    assert asset_service.purged_asset_ids == [1]
    assert view_model.assets[0].status == "purged"
    assert "1 files" not in view_model.feedback
    assert "Purged media for asset #1" in view_model.feedback


def test_asset_view_model_describes_references(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    report = view_model.describe_asset_references(1)

    assert report.asset_code == "hero_asset"
    assert view_model.status == "ready"
    assert view_model.feedback == "Loaded references for asset #1"


def test_asset_view_model_lists_replacement_candidates(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero_alt.mp4"),
        asset_code="hero_asset_v2",
    )

    candidates = view_model.list_replacement_candidates(1)

    assert [candidate.asset_code for candidate in candidates] == ["hero_asset_v2"]
    assert view_model.feedback == "Loaded replacement candidates for asset #1"


def test_asset_view_model_replaces_asset_in_recipes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    artifact_service = FakeArtifactGenerationService(asset_service)
    view_model = AssetLibraryViewModel(
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=artifact_service,
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )
    view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero_alt.mp4"),
        asset_code="hero_asset_v2",
    )

    report = view_model.replace_asset_in_recipes(1, 2)

    assert report.replaced_item_count == 2
    assert asset_service.replaced_pairs == [(1, 2)]
    assert view_model.feedback == "Replaced asset #1 with #2 in 1 recipe(s)"
