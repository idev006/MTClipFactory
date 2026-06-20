from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class AssetModel(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    asset_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    codec: Mapped[str | None] = mapped_column(String(64), nullable=True)
    has_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    proxy_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    alpha_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rgba_cache_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class TagModel(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("tag_name", "tag_group", name="uq_tags_name_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tag_group: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class AssetTagModel(Base):
    __tablename__ = "asset_tags"

    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class RecipeModel(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    recipe_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    target_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(64), nullable=True)
    script_angle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hook_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cta_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recipe_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duplicate_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate")
    decision_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class RecipeItemModel(Base):
    __tablename__ = "recipe_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OutputModel(Base):
    __tablename__ = "outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    output_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class DecisionEventModel(Base):
    __tablename__ = "decision_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    output_id: Mapped[int | None] = mapped_column(ForeignKey("outputs.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class CompositionPlanModel(Base):
    __tablename__ = "composition_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False, unique=True)
    duration_source: Mapped[str] = mapped_column(String(64), nullable=False)
    target_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    layer_assignments_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class RenderDecisionModel(Base):
    __tablename__ = "render_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    composition_plan_id: Mapped[int] = mapped_column(ForeignKey("composition_plans.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class TimelineSegmentModel(Base):
    __tablename__ = "timeline_segments"
    __table_args__ = (UniqueConstraint("composition_plan_id", "sequence_index", name="uq_timeline_segments_plan_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    composition_plan_id: Mapped[int] = mapped_column(ForeignKey("composition_plans.id"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    segment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    target_duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    message_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preferred_layers_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    text_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audio_policy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class ProductionOrderModel(Base):
    __tablename__ = "production_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    batch_code: Mapped[str] = mapped_column(String(128), nullable=False)
    source_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strict_fulfillment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preview_generation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    run_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_root: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_acquired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProductionOrderItemModel(Base):
    __tablename__ = "production_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    production_order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_code_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_output_count: Mapped[int] = mapped_column(Integer, nullable=False)
    target_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    uniqueness_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="batch")
    duration_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="voice_with_bounds")
    fixed_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_duration_sec: Mapped[float] = mapped_column(Float, nullable=False, default=12.0)
    max_duration_sec: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)


class ProductionOrderStageModel(Base):
    __tablename__ = "production_order_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    production_order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id"), nullable=False)
    production_order_item_id: Mapped[int | None] = mapped_column(ForeignKey("production_order_items.id"), nullable=True)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"), nullable=True)
    output_id: Mapped[int | None] = mapped_column(ForeignKey("outputs.id"), nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


class ProductionOrderEventModel(Base):
    __tablename__ = "production_order_events"
    __table_args__ = (
        UniqueConstraint("production_order_id", "sequence_index", name="uq_production_order_events_order_seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    production_order_id: Mapped[int] = mapped_column(ForeignKey("production_orders.id"), nullable=False)
    production_order_item_id: Mapped[int | None] = mapped_column(ForeignKey("production_order_items.id"), nullable=True)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stage_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
