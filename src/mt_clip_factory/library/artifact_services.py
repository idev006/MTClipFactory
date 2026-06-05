from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, UTC
from pathlib import Path

from mt_clip_factory.domain.enums import JobStatus
from mt_clip_factory.domain.jobs import Job
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.library.artifact_dto import ArtifactJobSummaryDTO
from mt_clip_factory.library.artifacts import FFmpegArtifactGenerator, build_artifact_job_code, encode_job_input


class ArtifactJobNotFoundError(ValueError):
    """Raised when an artifact job cannot be found."""


class ArtifactGenerationService:
    THUMBNAIL_JOB_TYPE = "generate_thumbnail"
    PROXY_JOB_TYPE = "generate_proxy"

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        artifact_generator: FFmpegArtifactGenerator,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._artifact_generator = artifact_generator

    def enqueue_thumbnail_job(self, asset_id: int) -> int:
        return self._enqueue_job(asset_id=asset_id, job_type=self.THUMBNAIL_JOB_TYPE)

    def enqueue_proxy_job(self, asset_id: int) -> int:
        return self._enqueue_job(asset_id=asset_id, job_type=self.PROXY_JOB_TYPE)

    def run_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise ArtifactJobNotFoundError(str(job_id))
            asset = uow.assets.get_by_id(job.asset_id or 0)
            if asset is None:
                raise ValueError(f"Unknown asset id for job {job_id}")
            product = uow.products.get_by_id(asset.product_id)
            if product is None:
                raise ValueError(f"Unknown product for asset {asset.id}")

            job.status = JobStatus.PROCESSING
            job.started_at = _utc_now()
            job.progress = 0.1
            uow.jobs.update(job)
            uow.commit()

            try:
                if job.job_type == self.THUMBNAIL_JOB_TYPE:
                    artifact_path = self._artifact_generator.generate_thumbnail(
                        source_file_path=Path(asset.file_path),
                        product_code=product.product_code,
                        asset_code=asset.asset_code,
                    )
                    asset.thumbnail_path = str(artifact_path)
                elif job.job_type == self.PROXY_JOB_TYPE:
                    artifact_path = self._artifact_generator.generate_proxy(
                        source_file_path=Path(asset.file_path),
                        product_code=product.product_code,
                        asset_code=asset.asset_code,
                    )
                    asset.proxy_path = str(artifact_path)
                else:
                    raise ValueError(f"Unsupported artifact job type: {job.job_type}")

                job.status = JobStatus.DONE
                job.progress = 1.0
                job.finished_at = _utc_now()
                job.error_message = None
                uow.assets.update(asset)
                uow.jobs.update(job)
                uow.commit()
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.progress = 0.0
                job.error_message = str(exc)
                job.finished_at = _utc_now()
                uow.jobs.update(job)
                uow.commit()
                raise

    def retry_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise ArtifactJobNotFoundError(str(job_id))
            job.status = JobStatus.QUEUED
            job.error_message = None
            job.started_at = None
            job.finished_at = None
            uow.jobs.update(job)
            uow.commit()
        self.run_job(job_id)

    def list_jobs(self, *, status: str | None = None) -> list[ArtifactJobSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                ArtifactJobSummaryDTO(
                    job_id=summary.job_id,
                    job_code=summary.job_code,
                    job_type=summary.job_type,
                    status=summary.status.value,
                    asset_id=summary.asset_id,
                    progress=summary.progress,
                    error_message=summary.error_message,
                )
                for summary in uow.jobs.list_summaries(status=status)
            ]

    def _enqueue_job(self, *, asset_id: int, job_type: str) -> int:
        with self._unit_of_work_factory() as uow:
            asset = uow.assets.get_by_id(asset_id)
            if asset is None:
                raise ValueError(str(asset_id))
            job = Job(
                job_code=build_artifact_job_code(job_type),
                job_type=job_type,
                asset_id=asset_id,
                status=JobStatus.QUEUED,
                input_json=encode_job_input({"asset_id": asset_id, "job_type": job_type}),
            )
            created = uow.jobs.add(job)
            uow.commit()
            if created.id is None:
                raise RuntimeError("Job identifier was not assigned.")
            return created.id


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
