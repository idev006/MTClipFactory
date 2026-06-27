from __future__ import annotations

import json
from pathlib import Path
from datetime import timedelta, timezone

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import ProductionOrderStage
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.production_order_risk_support import classify_near_duplicate_score
from mt_clip_factory.factory.production_order_service import (
    ProductionOrderAlreadyExistsError,
    ProductionOrderService,
)
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory import time_utils
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class FakeMetadataAnalyzer:
    def __init__(self, durations_by_name: dict[str, float]) -> None:
        self._durations_by_name = durations_by_name

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        duration_sec = self._durations_by_name.get(file_path.name, 12.0)
        is_audio = file_path.suffix.lower() == ".mp3"
        return AnalyzedMediaMetadata(
            duration_sec=duration_sec,
            width=None if is_audio else 1920,
            height=None if is_audio else 1080,
            fps=None if is_audio else 30.0,
            ratio=None if is_audio else "16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="aac" if is_audio else "h264",
            has_audio=True,
        )


def _build_asset_service(unit_of_work_factory, media_root: Path, durations_by_name: dict[str, float]) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(durations_by_name),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _build_factory_service(
    unit_of_work_factory,
    preview_root: Path,
    *,
    fail_preview_stems: set[str] | None = None,
) -> VideoAssemblyFactoryService:
    class FakePreviewRenderer:
        def render_output(
            self,
            *,
            product_code: str,
            output_stem: str,
            source_files: list[Path],
            segment_clips: tuple[PreviewSegmentClip, ...] = (),
            audio_mix_plan: PreviewAudioMixPlan | None = None,
            target_ratio: str | None = None,
            target_path: Path | None = None,
            fill_policies=None,
        ) -> RenderedPreviewOutput:
            del audio_mix_plan, target_ratio, fill_policies
            if fail_preview_stems and output_stem in fail_preview_stems:
                raise RuntimeError(f"synthetic preview failure for {output_stem}")
            resolved_target_path = target_path or (preview_root / product_code / "videos" / f"{output_stem}.mp4")
            resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                b"".join(segment.source_file.read_bytes() for segment in segment_clips)
                if segment_clips
                else source_files[0].read_bytes()
            )
            resolved_target_path.write_bytes(payload)
            duration_sec = round(sum(segment.target_duration_sec for segment in segment_clips), 3) if segment_clips else 3.0
            return RenderedPreviewOutput(
                file_path=resolved_target_path,
                duration_sec=duration_sec,
                audio_mix_summary=None,
                visual_composite_summary=None,
            )

    renderer = FakePreviewRenderer()
    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=renderer,
        final_renderer=renderer,
    )


def _register_asset(
    asset_service: AssetIntakeService,
    *,
    product_id: int,
    tmp_path: Path,
    asset_type: str,
    asset_code: str,
    file_name: str,
) -> int:
    source_file = tmp_path / file_name
    source_file.write_bytes(asset_code.encode("utf-8"))
    return asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type=asset_type,
            source_file_path=source_file,
            asset_code=asset_code,
        )
    )


def _build_services(
    unit_of_work_factory,
    tmp_path: Path,
    *,
    durations_by_name: dict[str, float] | None = None,
    fail_preview_stems: set[str] | None = None,
):
    durations = {} if durations_by_name is None else durations_by_name
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", durations)
    factory_service = _build_factory_service(
        unit_of_work_factory,
        tmp_path / "previews",
        fail_preview_stems=fail_preview_stems,
    )
    auto_factory_service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    production_order_service = ProductionOrderService(
        unit_of_work_factory=unit_of_work_factory,
        auto_factory_service=auto_factory_service,
    )
    return product_service, asset_service, factory_service, production_order_service


def test_production_order_service_persists_and_lists_orders(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="serum", product_name="Serum"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="launch_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="serum", requested_output_count=2),),
        ),
        source_mode="manual_batch",
        order_code="launch_batch_001",
        requested_by="planner_a",
    )

    summary = service.list_orders()[0]
    details = service.get_order(order_id)

    assert summary.production_order_id == order_id
    assert summary.order_code == "launch_batch_001"
    assert summary.status == "queued"
    assert summary.risk_level == "Unavailable"
    assert summary.max_near_duplicate_score is None
    assert summary.max_duplicate_truth_score is None
    assert details.production_order_id == order_id
    assert details.source_mode == "manual_batch"
    assert details.requested_by == "planner_a"
    assert details.items[0].creative_preset_mode == "auto_best_fit"
    assert details.items[0].creative_preset_codes == ()


def test_production_order_service_persists_creative_preset_request_truth(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="serum", product_name="Serum"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="launch_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="serum",
                    requested_output_count=2,
                    creative_preset_mode="preset_mix",
                    creative_preset_codes=("ugc_proof", "clinical_clean"),
                ),
            ),
        ),
        source_mode="manual_batch",
        order_code="launch_batch_creative_001",
    )

    details = service.get_order(order_id)

    assert details.items[0].creative_preset_mode == "preset_mix"
    assert details.items[0].creative_preset_codes == ("ugc_proof", "clinical_clean")
    assert len(details.items) == 1
    assert details.items[0].product_code == "serum"
    assert details.stages == ()

    with pytest.raises(ProductionOrderAlreadyExistsError):
        service.create_order(
            AutoFactoryBatchOrderDTO(
                batch_code="launch_batch",
                product_requests=(AutoFactoryProductRequestDTO(product_code="serum", requested_output_count=1),),
            ),
            source_mode="manual_batch",
            order_code="launch_batch_creative_001",
        )


def test_production_order_service_displays_local_operator_time(unit_of_work_factory, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(time_utils, "resolve_local_display_timezone", lambda: timezone(timedelta(hours=7)))
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="serum", product_name="Serum"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="launch_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="serum", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="launch_batch_001",
    )

    with unit_of_work_factory() as uow:
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        order.created_at = order.created_at.replace(year=2026, month=6, day=21, hour=7, minute=57, second=27, microsecond=0)
        order.started_at = order.created_at.replace(second=28)
        order.finished_at = order.created_at.replace(hour=8, minute=5, second=23)
        uow.production_orders.update(order)
        uow.commit()

    summary = service.list_orders()[0]
    details = service.get_order(order_id)

    assert summary.started_at == "2026-06-21 14:57:28"
    assert summary.finished_at == "2026-06-21 15:05:23"
    assert details.started_at == "2026-06-21 14:57:28"
    assert details.finished_at == "2026-06-21 15:05:23"


def test_production_order_service_runs_order_and_records_successful_stages(unit_of_work_factory, tmp_path) -> None:
    product_service, asset_service, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_id = product_service.create_product(CreateProductCommand(product_code="cream", product_name="Cream"))
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_02",
        file_name="fg02.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )

    details = service.create_and_run_order(
        AutoFactoryBatchOrderDTO(
            batch_code="cream_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="cream",
                    requested_output_count=1,
                    target_platform="shopee",
                    target_ratio="9:16",
                    fixed_duration_sec=15.0,
                ),
            ),
        ),
        source_mode="manual_batch",
        order_code="cream_order_001",
    )

    assert details.status == "succeeded"
    assert [stage.stage_name for stage in details.stages] == ["materialize", "preview", "review"]
    assert [stage.status for stage in details.stages] == ["succeeded", "succeeded", "succeeded"]
    assert details.stages[0].recipe_id is not None
    assert details.stages[1].job_id is not None
    assert details.stages[1].output_id is not None
    materialize_detail = json.loads(details.stages[0].detail_json or "{}")
    assert materialize_detail["recipe_code"] == "cream_cream_batch_001"
    assert "near_duplicate_score" in materialize_detail
    assert "near_duplicate_reasons" in materialize_detail
    assert "fingerprint" in materialize_detail
    assert "fingerprint_hash" in materialize_detail
    assert "caption_signature" in materialize_detail
    assert "main_caption_signature" in materialize_detail

    summary = service.list_orders()[0]
    expected_risk_level = classify_near_duplicate_score(float(materialize_detail["near_duplicate_score"]))

    assert summary.production_order_id == details.production_order_id
    assert summary.status == "succeeded"
    assert summary.risk_level == expected_risk_level
    assert summary.max_near_duplicate_score is not None
    assert summary.max_near_duplicate_score == pytest.approx(materialize_detail["near_duplicate_score"])


def test_production_order_service_succeeds_for_minimal_persistent_foreground_background_clip(
    unit_of_work_factory,
    tmp_path,
) -> None:
    product_service, asset_service, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_id = product_service.create_product(CreateProductCommand(product_code="toner", product_name="Toner"))
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )

    details = service.create_and_run_order(
        AutoFactoryBatchOrderDTO(
            batch_code="toner_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="toner",
                    requested_output_count=1,
                    fixed_duration_sec=15.0,
                ),
            ),
        ),
        source_mode="manual_batch",
        order_code="toner_order_001",
    )

    assert details.status == "succeeded"
    assert [stage.status for stage in details.stages] == ["succeeded", "succeeded", "succeeded"]


def test_production_order_service_records_retryable_preview_failure(unit_of_work_factory, tmp_path) -> None:
    product_service, asset_service, _, service = _build_services(
        unit_of_work_factory,
        tmp_path,
        fail_preview_stems={"mask_mask_batch_001"},
    )
    product_id = product_service.create_product(CreateProductCommand(product_code="mask", product_name="Mask"))
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )

    details = service.create_and_run_order(
        AutoFactoryBatchOrderDTO(
            batch_code="mask_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="mask",
                    requested_output_count=1,
                    fixed_duration_sec=15.0,
                ),
            ),
        ),
        source_mode="manual_batch",
        order_code="mask_order_001",
    )

    assert details.status == "failed_retryable"
    assert [stage.stage_name for stage in details.stages] == ["materialize", "preview"]
    assert details.stages[1].status == "failed_retryable"
    assert details.stages[1].failure_class == "preview_render_failure"
    assert "synthetic preview failure" in (details.stages[1].detail_json or "")


def test_production_order_service_recent_orders_use_render_truth_for_duplicate_score(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="serum", product_name="Serum"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="render_truth_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="serum", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="render_truth_order_001",
    )

    with unit_of_work_factory() as uow:
        item = uow.production_orders.list_items(order_id)[0]
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        order.status = OrchestrationStatus.SUCCEEDED
        uow.production_orders.update(order)
        uow.production_order_stages.add(
            ProductionOrderStage(
                production_order_id=order_id,
                production_order_item_id=item.id,
                stage_name="materialize",
                stage_scope="recipe",
                status=OrchestrationStatus.SUCCEEDED,
                sequence_index=1,
                recipe_id=101,
                detail_json=json.dumps({"near_duplicate_score": 0.2}),
            )
        )
        uow.production_order_stages.add(
            ProductionOrderStage(
                production_order_id=order_id,
                production_order_item_id=item.id,
                stage_name="preview",
                stage_scope="recipe",
                status=OrchestrationStatus.SUCCEEDED,
                sequence_index=2,
                recipe_id=101,
                output_id=201,
                detail_json=json.dumps({"duplicate_risk": 0.9, "history_scope": "auto_factory_preview"}),
            )
        )
        uow.commit()

    summary = service.list_orders()[0]

    assert summary.risk_level == "High"
    assert summary.max_near_duplicate_score == pytest.approx(0.2)
    assert summary.max_render_duplicate_score == pytest.approx(0.9)
    assert summary.max_duplicate_truth_score == pytest.approx(0.9)


def test_production_order_service_records_terminal_materialization_failure(unit_of_work_factory, tmp_path) -> None:
    product_service, asset_service, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_id = product_service.create_product(CreateProductCommand(product_code="soap", product_name="Soap"))
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_02",
        file_name="fg02.mp4",
    )

    details = service.create_and_run_order(
        AutoFactoryBatchOrderDTO(
            batch_code="soap_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="soap", requested_output_count=3),),
        ),
        source_mode="manual_batch",
        order_code="soap_order_001",
    )

    assert details.status == "failed_terminal"
    assert len(details.stages) == 1
    assert details.stages[0].stage_name == "materialize"
    assert details.stages[0].status == "failed_terminal"
    assert details.stages[0].failure_class == "planning_capacity_shortfall"


def test_production_order_service_pauses_at_safe_checkpoint(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="pauseable", product_name="Pauseable"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="pause_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="pauseable", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="pause_order_001",
    )

    with unit_of_work_factory() as uow:
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        now = utc_now()
        order.status = OrchestrationStatus.PROCESSING
        order.started_at = now
        order.lease_owner = "worker_a"
        order.lease_acquired_at = now
        order.lease_heartbeat_at = now
        order.lease_expires_at = now + timedelta(seconds=60)
        uow.production_orders.update(order)
        uow.commit()

    requested = service.request_pause(order_id)

    assert requested.status == "pause_requested"
    assert service._consume_control_checkpoint(order_id, worker_id="worker_a") == OrchestrationStatus.PAUSED

    paused = service.get_order(order_id)

    assert paused.status == "paused"
    assert paused.lease_owner is None
    assert [event.event_type for event in paused.events][-2:] == ["pause_requested", "paused"]


def test_production_order_service_stops_paused_order_immediately(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="stoppable", product_name="Stoppable"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="stop_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="stoppable", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="stop_order_001",
    )

    with unit_of_work_factory() as uow:
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        now = utc_now()
        order.status = OrchestrationStatus.PAUSED
        order.started_at = now
        uow.production_orders.update(order)
        uow.commit()

    stopped = service.request_stop(order_id)

    assert stopped.status == "stopped"
    assert stopped.lease_owner is None
    assert stopped.finished_at is not None
    assert stopped.events[-1].event_type == "stopped"


def test_production_order_service_stops_stale_active_order_immediately(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="stalestop", product_name="Stale Stop"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="stalestop_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="stalestop", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="stalestop_order_001",
    )

    with unit_of_work_factory() as uow:
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        now = utc_now()
        order.status = OrchestrationStatus.PROCESSING
        order.started_at = now - timedelta(minutes=3)
        order.lease_owner = "worker_a"
        order.lease_acquired_at = now - timedelta(minutes=3)
        order.lease_heartbeat_at = now - timedelta(minutes=2)
        order.lease_expires_at = now - timedelta(minutes=1)
        uow.production_orders.update(order)
        uow.commit()

    stopped = service.request_stop(order_id)

    assert stopped.status == "stopped"
    assert stopped.lease_owner is None
    assert stopped.lease_state == "released"
    assert stopped.finished_at is not None
    assert [event.event_type for event in stopped.events][-2:] == ["stop_requested", "stopped"]
    assert "stale" in stopped.events[-1].message.lower()


def test_production_order_service_resume_reuses_materialized_recipes_after_retryable_failure(
    unit_of_work_factory,
    tmp_path,
) -> None:
    fail_preview_stems = {"resume_resume_batch_001"}
    product_service, asset_service, _, service = _build_services(
        unit_of_work_factory,
        tmp_path,
        fail_preview_stems=fail_preview_stems,
    )
    product_id = product_service.create_product(CreateProductCommand(product_code="resume", product_name="Resume"))
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )

    first_run = service.create_and_run_order(
        AutoFactoryBatchOrderDTO(
            batch_code="resume_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="resume",
                    requested_output_count=1,
                    fixed_duration_sec=15.0,
                ),
            ),
        ),
        source_mode="manual_batch",
        order_code="resume_order_001",
    )

    assert first_run.status == "failed_retryable"

    fail_preview_stems.clear()
    resumed = service.resume_order(first_run.production_order_id)

    assert resumed.status == "succeeded"
    assert sum(1 for stage in resumed.stages if stage.stage_name == "materialize") == 1
    assert sum(1 for stage in resumed.stages if stage.stage_name == "preview") == 2
    assert any(event.event_type == "resume_requested" for event in resumed.events)


def test_production_order_service_marks_stale_leases_as_recoverable_in_details_and_summary(
    unit_of_work_factory,
    tmp_path,
) -> None:
    product_service, _, _, service = _build_services(unit_of_work_factory, tmp_path)
    product_service.create_product(CreateProductCommand(product_code="stale", product_name="Stale"))

    order_id = service.create_order(
        AutoFactoryBatchOrderDTO(
            batch_code="stale_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="stale", requested_output_count=1),),
        ),
        source_mode="manual_batch",
        order_code="stale_order_001",
    )

    with unit_of_work_factory() as uow:
        order = uow.production_orders.get_by_id(order_id)
        assert order is not None
        now = utc_now()
        order.status = OrchestrationStatus.PROCESSING
        order.started_at = now
        order.lease_owner = "worker_a"
        order.lease_acquired_at = now - timedelta(minutes=3)
        order.lease_heartbeat_at = now - timedelta(minutes=2)
        order.lease_expires_at = now - timedelta(minutes=1)
        uow.production_orders.update(order)
        uow.commit()

    details = service.get_order(order_id)
    summary = service.list_orders()[0]

    assert details.lease_is_stale is True
    assert details.lease_state == "stale"
    assert details.recovery_state == "stale"
    assert details.suggested_action == "resume_recover_stale"
    assert summary.lease_state == "stale"
    assert summary.recovery_state == "stale"
    assert summary.suggested_action == "resume_recover_stale"
