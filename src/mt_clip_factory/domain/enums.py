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

