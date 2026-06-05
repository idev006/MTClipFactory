from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.enums import JobStatus
from mt_clip_factory.domain.jobs import Job, JobSummary
from mt_clip_factory.infrastructure.models import JobModel


class SqlAlchemyJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: Job) -> Job:
        model = JobModel(
            job_code=job.job_code,
            job_type=job.job_type,
            recipe_id=job.recipe_id,
            asset_id=job.asset_id,
            status=job.status.value,
            priority=job.priority,
            progress=job.progress,
            worker_id=job.worker_id,
            input_json=job.input_json,
            output_json=job.output_json,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self._session.add(model)
        self._session.flush()
        job.id = model.id
        return job

    def get_by_id(self, job_id: int) -> Job | None:
        model = self._session.get(JobModel, job_id)
        if model is None:
            return None
        return self._to_entity(model)

    def list_summaries(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
    ) -> Sequence[JobSummary]:
        statement = select(JobModel).order_by(JobModel.created_at.desc(), JobModel.id.desc())
        if status is not None:
            statement = statement.where(JobModel.status == status)
        if job_type is not None:
            statement = statement.where(JobModel.job_type == job_type)
        rows = self._session.execute(statement).scalars().all()
        return [
            JobSummary(
                job_id=row.id,
                job_code=row.job_code,
                job_type=row.job_type,
                status=JobStatus(row.status),
                asset_id=row.asset_id,
                recipe_id=row.recipe_id,
                progress=row.progress,
                error_message=row.error_message,
            )
            for row in rows
        ]

    def update(self, job: Job) -> Job:
        if job.id is None:
            raise ValueError("Job id is required for update.")
        model = self._session.get(JobModel, job.id)
        if model is None:
            raise ValueError(f"Unknown job id: {job.id}")
        model.status = job.status.value
        model.priority = job.priority
        model.progress = job.progress
        model.worker_id = job.worker_id
        model.input_json = job.input_json
        model.output_json = job.output_json
        model.error_message = job.error_message
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        self._session.flush()
        return job

    def _to_entity(self, model: JobModel) -> Job:
        return Job(
            id=model.id,
            job_code=model.job_code,
            job_type=model.job_type,
            recipe_id=model.recipe_id,
            asset_id=model.asset_id,
            status=JobStatus(model.status),
            priority=model.priority,
            progress=model.progress,
            worker_id=model.worker_id,
            input_json=model.input_json,
            output_json=model.output_json,
            error_message=model.error_message,
            created_at=model.created_at,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )
