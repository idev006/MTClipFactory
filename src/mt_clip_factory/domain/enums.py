from __future__ import annotations

from enum import StrEnum


class AssetType(StrEnum):
    BACKGROUND_VIDEO = "background_video"
    FOREGROUND_VIDEO = "foreground_video"
    VOICEOVER = "voiceover"
    BACKGROUND_MUSIC = "background_music"
    SFX = "sfx"
    TEMPLATE = "template"
    SCRIPT = "script"


class RecipeStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class JobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrchestrationStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    PROCESSING = "processing"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    STOP_REQUESTED = "stop_requested"
    STOPPED = "stopped"
    RESUME_REQUESTED = "resume_requested"
    SUCCEEDED = "succeeded"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
