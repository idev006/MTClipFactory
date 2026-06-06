from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.domain.enums import JobStatus
from mt_clip_factory.library.artifact_services import ArtifactGenerationService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=2.0,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="h264",
            has_audio=True,
        )


class FakeArtifactGenerator:
    def __init__(self, media_root: Path, *, fail_once: bool = False) -> None:
        self._media_root = media_root
        self._fail_once = fail_once
        self.calls: list[tuple[str, str]] = []

    def generate_thumbnail(self, source_file_path: Path, product_code: str, asset_code: str) -> Path:
        return self._generate(
            artifact_kind="thumbnail",
            source_file_path=source_file_path,
            product_code=product_code,
            asset_code=asset_code,
            suffix=".jpg",
        )

    def generate_proxy(self, source_file_path: Path, product_code: str, asset_code: str) -> Path:
        return self._generate(
            artifact_kind="proxy",
            source_file_path=source_file_path,
            product_code=product_code,
            asset_code=asset_code,
            suffix=".mp4",
        )

    def _generate(
        self,
        *,
        artifact_kind: str,
        source_file_path: Path,
        product_code: str,
        asset_code: str,
        suffix: str,
    ) -> Path:
        self.calls.append((artifact_kind, asset_code))
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError(f"{artifact_kind} generation failed")

        artifact_dir = self._media_root / "products" / product_code / "cache" / f"{artifact_kind}s"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        target_path = artifact_dir / f"{asset_code}{suffix}"
        target_path.write_bytes(source_file_path.read_bytes())
        return target_path


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _register_asset(unit_of_work_factory, tmp_path: Path) -> tuple[AssetIntakeService, int]:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )
    return asset_service, asset_id


def test_artifact_service_generates_thumbnail_and_updates_asset(unit_of_work_factory, tmp_path) -> None:
    asset_service, asset_id = _register_asset(unit_of_work_factory, tmp_path)
    generator = FakeArtifactGenerator(tmp_path / "media_library")
    service = ArtifactGenerationService(unit_of_work_factory=unit_of_work_factory, artifact_generator=generator)

    job_id = service.enqueue_thumbnail_job(asset_id)
    service.run_job(job_id)

    assets = asset_service.list_assets()
    jobs = service.list_jobs()
    assert assets[0].thumbnail_path is not None
    assert Path(assets[0].thumbnail_path).exists()
    assert assets[0].proxy_path is None
    assert jobs[0].status == JobStatus.DONE.value
    assert generator.calls == [("thumbnail", "hero_asset")]


def test_artifact_service_generates_proxy_and_updates_asset(unit_of_work_factory, tmp_path) -> None:
    asset_service, asset_id = _register_asset(unit_of_work_factory, tmp_path)
    generator = FakeArtifactGenerator(tmp_path / "media_library")
    service = ArtifactGenerationService(unit_of_work_factory=unit_of_work_factory, artifact_generator=generator)

    job_id = service.enqueue_proxy_job(asset_id)
    service.run_job(job_id)

    assets = asset_service.list_assets()
    jobs = service.list_jobs()
    assert assets[0].proxy_path is not None
    assert Path(assets[0].proxy_path).exists()
    assert assets[0].thumbnail_path is None
    assert jobs[0].status == JobStatus.DONE.value
    assert generator.calls == [("proxy", "hero_asset")]


def test_artifact_service_marks_failed_job_and_supports_retry(unit_of_work_factory, tmp_path) -> None:
    asset_service, asset_id = _register_asset(unit_of_work_factory, tmp_path)
    generator = FakeArtifactGenerator(tmp_path / "media_library", fail_once=True)
    service = ArtifactGenerationService(unit_of_work_factory=unit_of_work_factory, artifact_generator=generator)

    job_id = service.enqueue_thumbnail_job(asset_id)

    with pytest.raises(RuntimeError, match="thumbnail generation failed"):
        service.run_job(job_id)

    failed_jobs = service.list_jobs(status="failed")
    assert len(failed_jobs) == 1
    assert failed_jobs[0].job_id == job_id
    assert failed_jobs[0].error_message == "thumbnail generation failed"
    assert failed_jobs[0].consecutive_failure_count == 1
    assert failed_jobs[0].recovery_attempt_count == 0
    assert asset_service.list_assets()[0].thumbnail_path is None

    service.retry_job(job_id)

    jobs = service.list_jobs()
    assert jobs[0].status == JobStatus.DONE.value
    assert jobs[0].error_message is None
    assert jobs[0].recovery_attempt_count == 1
    assert jobs[0].consecutive_failure_count == 0
    assert asset_service.list_assets()[0].thumbnail_path is not None
