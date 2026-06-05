from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata


@dataclass(slots=True, frozen=True)
class AssetReadinessDecision:
    status: str
    reason: str


class AssetReadinessEvaluator:
    def evaluate(self, asset_type: AssetType, metadata: AnalyzedMediaMetadata) -> AssetReadinessDecision:
        if asset_type in {
            AssetType.BACKGROUND_VIDEO,
            AssetType.FOREGROUND_VIDEO,
            AssetType.TEMPLATE,
        }:
            if metadata.width and metadata.height and metadata.duration_sec and metadata.duration_sec > 0:
                return AssetReadinessDecision(status="ready", reason="video_metadata_complete")
            return AssetReadinessDecision(status="needs_review", reason="missing_video_metadata")

        if asset_type in {AssetType.VOICEOVER, AssetType.BACKGROUND_MUSIC, AssetType.SFX}:
            if metadata.duration_sec and metadata.duration_sec > 0:
                return AssetReadinessDecision(status="ready", reason="audio_metadata_complete")
            return AssetReadinessDecision(status="needs_review", reason="missing_audio_duration")

        if asset_type == AssetType.SCRIPT:
            if metadata.file_size_mb is not None and metadata.file_size_mb > 0:
                return AssetReadinessDecision(status="ready", reason="document_present")
            return AssetReadinessDecision(status="needs_review", reason="empty_document")

        return AssetReadinessDecision(status="needs_review", reason="unsupported_asset_type")
