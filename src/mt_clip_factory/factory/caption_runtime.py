from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tomllib

from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_layout import CaptionFrameContext, resolve_caption_layout
from mt_clip_factory.factory.caption_runtime_support import (
    CaptionContractError,
    _bounded_float,
    _boolean,
    _choice_text,
    _escape_toml_string,
    _non_negative_int,
    _optional_text,
    _positive_int,
    _resolve_font,
    _resolve_style_preset_defaults,
    _text_list,
)
from mt_clip_factory.factory.visual_selection import seeded_choice, seeded_cycled_choice


@dataclass(slots=True, frozen=True)
class CaptionSelectionPolicy:
    mode: str = "random_with_seed"
    seed_scope: str = "recipe"


@dataclass(slots=True, frozen=True)
class CaptionPool:
    main: tuple[str, ...] = ()
    sub: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class CaptionRoleStyle:
    position: str
    alignment: str
    vertical_alignment: str
    textbox_alignment: str
    textbox_mode: str
    textbox_height_mode: str
    style_preset: str | None
    font_family: str
    font_fallbacks: tuple[str, ...]
    font_size: int
    font_size_unit: str
    min_font_size: int
    font_weight: str
    text_color: str
    stroke_color: str
    stroke_width: int
    background_color: str | None
    background_opacity: float
    box_border_color: str | None
    box_border_opacity: float
    box_border_width: int
    padding: int
    max_lines: int
    preferred_line_count: int
    max_chars_per_line: int
    max_width_ratio: float
    textbox_width_ratio: float
    textbox_height_ratio: float
    line_spacing_ratio: float
    line_advance_ratio: float
    safe_top_ratio: float
    safe_bottom_ratio: float
    max_safe_band_height_ratio: float
    overflow_policy: str
    enter_animation: str | None
    review_required_if_overflow: bool


@dataclass(slots=True, frozen=True)
class ProductCaptionContract:
    selection: CaptionSelectionPolicy
    pools: dict[str, CaptionPool]
    main_style: CaptionRoleStyle
    sub_style: CaptionRoleStyle


@dataclass(slots=True, frozen=True)
class ResolvedCaptionRole:
    role: str
    source_text: str
    rendered_text: str
    rendered_lines: tuple[str, ...]
    segment_type: str
    sequence_index: int
    seed_key: str
    selection_index: int
    line_break_mode: str
    fit_strategy: str
    line_count: int
    font_family: str
    font_fallbacks: tuple[str, ...]
    font_size: int
    requested_font_size: int
    font_size_unit: str
    min_font_size: int
    font_weight: str
    font_source: str
    font_file: Path | None
    font_resolution_mode: str
    font_resolution_target: str
    position: str
    alignment: str
    vertical_alignment: str
    textbox_alignment: str
    textbox_height_mode: str
    style_preset: str | None
    text_color: str
    stroke_color: str
    stroke_width: int
    background_color: str | None
    background_opacity: float
    box_border_color: str | None
    box_border_opacity: float
    box_border_width: int
    padding: int
    max_lines: int
    preferred_line_count: int
    max_chars_per_line: int
    max_width_ratio: float
    textbox_width_ratio: float
    textbox_height_ratio: float
    line_spacing_ratio: float
    line_advance_ratio: float
    safe_top_ratio: float
    safe_bottom_ratio: float
    max_safe_band_height_ratio: float
    effective_safe_bottom_ratio: float
    line_spacing_px: int
    line_font_sizes_px: tuple[int, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    line_heights_px: tuple[int, ...]
    text_block_width_px: int
    text_block_height_px: int
    max_text_width_px: int
    line_left_positions_px: tuple[int, ...]
    line_top_positions_px: tuple[int, ...]
    textbox_mode: str
    line_box_left_positions_px: tuple[int, ...]
    line_box_top_positions_px: tuple[int, ...]
    line_box_widths_px: tuple[int, ...]
    line_box_heights_px: tuple[int, ...]
    box_left_px: int
    box_top_px: int
    box_width_px: int
    box_height_px: int
    frame_width_px: int
    frame_height_px: int
    overflow_policy: str
    enter_animation: str | None
    overflowed: bool
    review_required: bool
    truncated_for_runtime: bool


@dataclass(slots=True, frozen=True)
class ResolvedSegmentCaptions:
    sequence_index: int
    segment_type: str
    roles: tuple[ResolvedCaptionRole, ...]


@dataclass(slots=True, frozen=True)
class ProductAutomationRuntimeContext:
    product_code: str
    source_product_dir: Path
    last_batch_code: str | None = None
    last_synced_at: str | None = None


class ProductAutomationMetadataStore:
    def __init__(self, media_root: Path) -> None:
        self._media_root = Path(media_root)

    def sync_caption_contract(self, *, product_code: str, source_file: Path | None) -> Path | None:
        target_path = self.caption_contract_path(product_code)
        if source_file is None or not source_file.exists():
            target_path.unlink(missing_ok=True)
            return None
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_path)
        return target_path

    def caption_contract_path(self, product_code: str) -> Path:
        return self._media_root / "products" / product_code / "automation" / "captions.toml"

    def sync_pipeline_contract(self, *, product_code: str, source_file: Path | None) -> Path | None:
        target_path = self.pipeline_contract_path(product_code)
        if source_file is None or not source_file.exists():
            target_path.unlink(missing_ok=True)
            return None
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_path)
        return target_path

    def pipeline_contract_path(self, product_code: str) -> Path:
        return self._media_root / "products" / product_code / "automation" / "pipeline.toml"

    def load_caption_contract_text(self, product_code: str) -> str | None:
        target_path = self.caption_contract_path(product_code)
        if not target_path.exists():
            return None
        return target_path.read_text(encoding="utf-8")

    def load_pipeline_contract_text(self, product_code: str) -> str | None:
        target_path = self.pipeline_contract_path(product_code)
        if not target_path.exists():
            return None
        return target_path.read_text(encoding="utf-8")

    def sync_runtime_context(
        self,
        *,
        product_code: str,
        source_product_dir: Path,
        batch_code: str | None = None,
        synced_at: str | None = None,
    ) -> Path:
        target_path = self.runtime_context_path(product_code)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f'product_code = "{_escape_toml_string(product_code)}"',
            f'source_product_dir = "{_escape_toml_string(str(Path(source_product_dir).resolve()))}"',
        ]
        if batch_code:
            lines.append(f'last_batch_code = "{_escape_toml_string(batch_code)}"')
        if synced_at:
            lines.append(f'last_synced_at = "{_escape_toml_string(synced_at)}"')
        target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return target_path

    def runtime_context_path(self, product_code: str) -> Path:
        return self._media_root / "products" / product_code / "automation" / "context.toml"

    def load_runtime_context(self, product_code: str) -> ProductAutomationRuntimeContext | None:
        target_path = self.runtime_context_path(product_code)
        if not target_path.exists():
            return None
        with target_path.open("rb") as file_handle:
            data = tomllib.load(file_handle)
        if not isinstance(data, dict):
            return None
        source_product_dir = _optional_text(data.get("source_product_dir"))
        if source_product_dir is None:
            return None
        return ProductAutomationRuntimeContext(
            product_code=_optional_text(data.get("product_code")) or product_code,
            source_product_dir=Path(source_product_dir),
            last_batch_code=_optional_text(data.get("last_batch_code")),
            last_synced_at=_optional_text(data.get("last_synced_at")),
        )


class CaptionRuntimeService:
    def __init__(self, *, metadata_store: ProductAutomationMetadataStore, fonts_root: Path) -> None:
        self._metadata_store = metadata_store
        self._fonts_root = Path(fonts_root)

    def resolve_for_segments(
        self,
        *,
        product_code: str,
        recipe_code: str,
        segments: tuple[TimelineSegment, ...],
        frame_width_px: int | None = None,
        frame_height_px: int | None = None,
    ) -> tuple[ResolvedSegmentCaptions, ...]:
        contract = self._load_contract(product_code)
        if contract is None:
            return ()
        frame = (
            None
            if frame_width_px is None or frame_height_px is None
            else CaptionFrameContext(width_px=frame_width_px, height_px=frame_height_px)
        )
        resolved_segments: list[ResolvedSegmentCaptions] = []
        for segment in segments:
            pool = contract.pools.get(segment.segment_type)
            if pool is None:
                continue
            roles: list[ResolvedCaptionRole] = []
            if pool.main:
                roles.append(
                    self._resolve_role(
                        product_code=product_code,
                        recipe_code=recipe_code,
                        segment=segment,
                        role="main",
                        options=pool.main,
                        style=contract.main_style,
                        selection=contract.selection,
                        frame=frame,
                    )
                )
            if pool.sub:
                roles.append(
                    self._resolve_role(
                        product_code=product_code,
                        recipe_code=recipe_code,
                        segment=segment,
                        role="sub",
                        options=pool.sub,
                        style=contract.sub_style,
                        selection=contract.selection,
                        frame=frame,
                    )
                )
            if roles:
                resolved_segments.append(
                    ResolvedSegmentCaptions(
                        sequence_index=segment.sequence_index,
                        segment_type=segment.segment_type,
                        roles=tuple(roles),
                    )
                )
        return tuple(resolved_segments)

    def _load_contract(self, product_code: str) -> ProductCaptionContract | None:
        raw_text = self._metadata_store.load_caption_contract_text(product_code)
        if raw_text is None:
            return None
        try:
            data = tomllib.loads(raw_text)
        except tomllib.TOMLDecodeError as exc:
            raise CaptionContractError(f"Invalid captions.toml for {product_code}: {exc}") from exc
        if not isinstance(data, dict):
            raise CaptionContractError(f"Invalid caption contract object for {product_code}.")
        selection_section = _expect_table(data.get("caption_selection"), table_name="[caption_selection]", required=False)
        pools_section = _expect_table(data.get("caption_pools"), table_name="[caption_pools]", required=False)
        properties_section = _expect_table(data.get("caption_properties"), table_name="[caption_properties]", required=False)
        return ProductCaptionContract(
            selection=CaptionSelectionPolicy(
                mode=_optional_text(selection_section.get("mode")) or "random_with_seed",
                seed_scope=_optional_text(selection_section.get("seed_scope")) or "recipe",
            ),
            pools={
                segment_type.casefold(): CaptionPool(
                    main=_text_list(pool_section.get("main"), context=f"[caption_pools.{segment_type}].main"),
                    sub=_text_list(pool_section.get("sub"), context=f"[caption_pools.{segment_type}].sub"),
                )
                for segment_type, pool_section in pools_section.items()
                if isinstance(pool_section, dict)
            },
            main_style=_parse_role_style(properties_section.get("main"), role="main"),
            sub_style=_parse_role_style(properties_section.get("sub"), role="sub"),
        )

    def _resolve_role(
        self,
        *,
        product_code: str,
        recipe_code: str,
        segment: TimelineSegment,
        role: str,
        options: tuple[str, ...],
        style: CaptionRoleStyle,
        selection: CaptionSelectionPolicy,
        frame: CaptionFrameContext | None,
    ) -> ResolvedCaptionRole:
        selection_index, seed_key = _select_index(
            option_count=len(options),
            product_code=product_code,
            recipe_code=recipe_code,
            segment=segment,
            role=role,
            seed_scope=selection.seed_scope,
        )
        source_text = options[selection_index]
        font_file, resolved_font_name, resolution_mode = _resolve_font(
            fonts_root=self._fonts_root,
            font_family=style.font_family,
            fallbacks=style.font_fallbacks,
        )
        layout = resolve_caption_layout(
            source_text=source_text,
            frame=frame,
            font_family=style.font_family,
            font_file=font_file,
            requested_font_size=style.font_size,
            font_size_unit=style.font_size_unit,
            min_font_size=style.min_font_size,
            max_lines=style.max_lines,
            preferred_line_count=style.preferred_line_count,
            max_chars_per_line=style.max_chars_per_line,
            textbox_mode=style.textbox_mode,
            textbox_height_mode=style.textbox_height_mode,
            textbox_width_ratio=style.textbox_width_ratio,
            textbox_height_ratio=style.textbox_height_ratio,
            textbox_alignment=style.textbox_alignment,
            line_spacing_ratio=style.line_spacing_ratio,
            line_advance_ratio=style.line_advance_ratio,
            padding=style.padding,
            alignment=style.alignment,
            vertical_alignment=style.vertical_alignment,
            position=style.position,
            stroke_width=style.stroke_width,
            safe_top_ratio=style.safe_top_ratio,
            safe_bottom_ratio=style.safe_bottom_ratio,
            max_safe_band_height_ratio=style.max_safe_band_height_ratio,
            overflow_policy=style.overflow_policy,
            review_required_if_overflow=style.review_required_if_overflow,
        )
        font_source = str(font_file) if font_file is not None else resolved_font_name
        return ResolvedCaptionRole(
            role=role,
            source_text=source_text,
            rendered_text=layout.rendered_text,
            rendered_lines=layout.rendered_lines,
            segment_type=segment.segment_type,
            sequence_index=segment.sequence_index,
            seed_key=seed_key,
            selection_index=selection_index,
            line_break_mode=layout.line_break_mode,
            fit_strategy=layout.fit_strategy,
            line_count=len(layout.rendered_lines),
            font_family=style.font_family,
            font_fallbacks=style.font_fallbacks,
            font_size=layout.font_size_px,
            requested_font_size=style.font_size,
            font_size_unit=style.font_size_unit,
            min_font_size=style.min_font_size,
            font_weight=style.font_weight,
            font_source=font_source,
            font_file=font_file,
            font_resolution_mode=resolution_mode,
            font_resolution_target=resolved_font_name,
            position=style.position,
            alignment=style.alignment,
            vertical_alignment=style.vertical_alignment,
            textbox_alignment=style.textbox_alignment,
            textbox_height_mode=style.textbox_height_mode,
            style_preset=style.style_preset,
            text_color=style.text_color,
            stroke_color=style.stroke_color,
            stroke_width=style.stroke_width,
            background_color=style.background_color,
            background_opacity=style.background_opacity,
            box_border_color=style.box_border_color,
            box_border_opacity=style.box_border_opacity,
            box_border_width=style.box_border_width,
            padding=style.padding,
            max_lines=style.max_lines,
            preferred_line_count=style.preferred_line_count,
            max_chars_per_line=style.max_chars_per_line,
            max_width_ratio=style.max_width_ratio,
            textbox_width_ratio=style.textbox_width_ratio,
            textbox_height_ratio=style.textbox_height_ratio,
            line_spacing_ratio=style.line_spacing_ratio,
            line_advance_ratio=style.line_advance_ratio,
            safe_top_ratio=style.safe_top_ratio,
            safe_bottom_ratio=style.safe_bottom_ratio,
            max_safe_band_height_ratio=style.max_safe_band_height_ratio,
            effective_safe_bottom_ratio=layout.effective_safe_bottom_ratio,
            line_spacing_px=layout.line_spacing_px,
            line_font_sizes_px=layout.line_font_sizes_px,
            line_widths_px=layout.line_widths_px,
            line_height_px=layout.line_height_px,
            line_heights_px=layout.line_heights_px,
            text_block_width_px=layout.text_block_width_px,
            text_block_height_px=layout.text_block_height_px,
            max_text_width_px=layout.max_text_width_px,
            line_left_positions_px=layout.line_left_positions_px,
            line_top_positions_px=layout.line_top_positions_px,
            textbox_mode=layout.textbox_mode,
            line_box_left_positions_px=layout.line_box_left_positions_px,
            line_box_top_positions_px=layout.line_box_top_positions_px,
            line_box_widths_px=layout.line_box_widths_px,
            line_box_heights_px=layout.line_box_heights_px,
            box_left_px=layout.box_left_px,
            box_top_px=layout.box_top_px,
            box_width_px=layout.box_width_px,
            box_height_px=layout.box_height_px,
            frame_width_px=layout.frame_width_px,
            frame_height_px=layout.frame_height_px,
            overflow_policy=style.overflow_policy,
            enter_animation=style.enter_animation,
            overflowed=layout.overflowed,
            review_required=layout.review_required,
            truncated_for_runtime=layout.truncated_for_runtime,
        )


def _expect_table(value, *, table_name: str, required: bool) -> dict[str, object]:
    if value is None:
        if required:
            raise CaptionContractError(f"Missing {table_name} table.")
        return {}
    if not isinstance(value, dict):
        raise CaptionContractError(f"Expected table {table_name}.")
    return value


def _parse_role_style(value, *, role: str) -> CaptionRoleStyle:
    section = _expect_table(value, table_name=f"[caption_properties.{role}]", required=False)
    style_preset = _optional_text(section.get("style_preset"))
    preset_defaults = _resolve_style_preset_defaults(style_preset=style_preset, role=role)
    default_position = "top" if role == "main" else "bottom"
    default_font_size = 72 if role == "main" else 40
    default_min_font_size = 48 if role == "main" else 30
    default_padding = 20 if role == "main" else 16
    default_max_lines = 3
    default_max_chars = 18 if role == "main" else 28
    default_max_width = 0.68 if role == "main" else 0.74
    default_overflow_policy = "wrap_then_scale_then_review" if role == "main" else "wrap_then_truncate_or_review"
    default_animation = "pop_in" if role == "main" else "fade_in"
    default_safe_top = 0.14 if role == "main" else 0.64
    default_safe_bottom = 0.46 if role == "main" else 0.88

    def value_for(*keys: str):
        for key in keys:
            if key in section:
                return section[key]
        for key in keys:
            if key in preset_defaults:
                return preset_defaults[key]
        return None

    textbox_width_ratio = _bounded_float(
        value_for("textbox_width_ratio", "max_width_ratio"),
        default=default_max_width,
        minimum=0.1,
        maximum=1.0,
        context=f"[caption_properties.{role}].textbox_width_ratio",
    )
    textbox_mode = _choice_text(
        value_for("textbox_mode"),
        default="grouped",
        allowed=("grouped", "per_line"),
        context=f"[caption_properties.{role}].textbox_mode",
    )
    textbox_height_mode = _choice_text(
        value_for("textbox_height_mode"),
        default="content_hug",
        allowed=("content_hug", "fixed"),
        context=f"[caption_properties.{role}].textbox_height_mode",
    )
    max_lines = _positive_int(value_for("max_lines"), default=default_max_lines, context=f"[caption_properties.{role}].max_lines")
    preferred_line_count = min(
        max_lines,
        _positive_int(
            value_for("preferred_line_count"),
            default=max_lines,
            context=f"[caption_properties.{role}].preferred_line_count",
        ),
    )
    resolved_position = _optional_text(value_for("position")) or default_position
    default_max_safe_band_height = 0.18 if role == "main" and resolved_position.casefold() == "top" else 0.0
    return CaptionRoleStyle(
        position=resolved_position,
        alignment=_optional_text(value_for("alignment")) or "center",
        vertical_alignment=_optional_text(value_for("vertical_alignment")) or "top",
        textbox_alignment=_optional_text(value_for("textbox_alignment")) or "center",
        textbox_mode=textbox_mode,
        textbox_height_mode=textbox_height_mode,
        style_preset=style_preset.casefold() if style_preset else None,
        font_family=_optional_text(value_for("font_family")) or "Arial",
        font_fallbacks=_text_list(value_for("font_fallbacks"), context=f"[caption_properties.{role}].font_fallbacks"),
        font_size=_positive_int(value_for("font_size"), default=default_font_size, context=f"[caption_properties.{role}].font_size"),
        font_size_unit=_optional_text(value_for("font_size_unit")) or "px",
        min_font_size=_positive_int(
            value_for("min_font_size"),
            default=default_min_font_size,
            context=f"[caption_properties.{role}].min_font_size",
        ),
        font_weight=_optional_text(value_for("font_weight")) or ("bold" if role == "main" else "medium"),
        text_color=_optional_text(value_for("text_color")) or "#FFFFFF",
        stroke_color=_optional_text(value_for("stroke_color")) or "#000000",
        stroke_width=_non_negative_int(
            value_for("stroke_width"),
            default=3 if role == "main" else 2,
            context=f"[caption_properties.{role}].stroke_width",
        ),
        background_color=_optional_text(value_for("background_color")),
        background_opacity=_bounded_float(
            value_for("background_opacity"),
            default=0.15 if role == "main" else 0.30,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].background_opacity",
        ),
        box_border_color=_optional_text(value_for("box_border_color")),
        box_border_opacity=_bounded_float(
            value_for("box_border_opacity"),
            default=0.0,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].box_border_opacity",
        ),
        box_border_width=_non_negative_int(
            value_for("box_border_width"),
            default=0,
            context=f"[caption_properties.{role}].box_border_width",
        ),
        padding=_non_negative_int(value_for("padding"), default=default_padding, context=f"[caption_properties.{role}].padding"),
        max_lines=max_lines,
        preferred_line_count=preferred_line_count,
        max_chars_per_line=_positive_int(
            value_for("max_chars_per_line"),
            default=default_max_chars,
            context=f"[caption_properties.{role}].max_chars_per_line",
        ),
        max_width_ratio=_bounded_float(
            value_for("max_width_ratio"),
            default=default_max_width,
            minimum=0.1,
            maximum=1.0,
            context=f"[caption_properties.{role}].max_width_ratio",
        ),
        textbox_width_ratio=textbox_width_ratio,
        textbox_height_ratio=_bounded_float(
            value_for("textbox_height_ratio"),
            default=0.0,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].textbox_height_ratio",
        ),
        line_spacing_ratio=_bounded_float(
            value_for("line_spacing_ratio"),
            default=0.12 if role == "main" else 0.16,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].line_spacing_ratio",
        ),
        line_advance_ratio=_bounded_float(
            value_for("line_advance_ratio"),
            default=1.0,
            minimum=0.5,
            maximum=1.2,
            context=f"[caption_properties.{role}].line_advance_ratio",
        ),
        safe_top_ratio=_bounded_float(
            value_for("safe_top_ratio"),
            default=default_safe_top,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].safe_top_ratio",
        ),
        safe_bottom_ratio=_bounded_float(
            value_for("safe_bottom_ratio"),
            default=default_safe_bottom,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].safe_bottom_ratio",
        ),
        max_safe_band_height_ratio=_bounded_float(
            value_for("max_safe_band_height_ratio"),
            default=default_max_safe_band_height,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].max_safe_band_height_ratio",
        ),
        overflow_policy=_optional_text(value_for("overflow_policy")) or default_overflow_policy,
        enter_animation=_optional_text(value_for("enter_animation")) or default_animation,
        review_required_if_overflow=_boolean(
            value_for("review_required_if_overflow"),
            default=True,
            context=f"[caption_properties.{role}].review_required_if_overflow",
        ),
    )


def _select_index(
    *,
    option_count: int,
    product_code: str,
    recipe_code: str,
    segment: TimelineSegment,
    role: str,
    seed_scope: str,
) -> tuple[int, str]:
    if option_count <= 0:
        raise CaptionContractError("Caption option count must be greater than zero.")
    normalized_scope = seed_scope.strip().casefold()
    if normalized_scope == "batch":
        batch_seed_key, batch_position = _resolve_batch_seed_context(
            product_code=product_code,
            recipe_code=recipe_code,
            segment=segment,
            role=role,
        )
        selection_index = seeded_cycled_choice(
            tuple(range(option_count)),
            seed_key=batch_seed_key,
            position=batch_position,
        )
        seed_key = f"{batch_seed_key}|cycle_position={batch_position}"
        return selection_index, seed_key
    seed_key = "|".join(
        (
            normalized_scope or "recipe",
            product_code,
            recipe_code,
            segment.segment_type,
            str(segment.sequence_index),
            role,
        )
    )
    selection_index = seeded_choice(tuple(range(option_count)), seed_key=seed_key)
    return selection_index, seed_key


def _resolve_batch_seed_context(
    *,
    product_code: str,
    recipe_code: str,
    segment: TimelineSegment,
    role: str,
) -> tuple[str, int]:
    batch_recipe_code, batch_position = _split_batch_recipe_code(recipe_code)
    seed_key = "|".join(
        (
            "batch",
            product_code,
            batch_recipe_code,
            segment.segment_type,
            str(segment.sequence_index),
            role,
        )
    )
    return seed_key, batch_position


def _split_batch_recipe_code(recipe_code: str) -> tuple[str, int]:
    prefix, separator, suffix = recipe_code.rpartition("_")
    if separator and suffix.isdigit():
        return prefix, max(0, int(suffix) - 1)
    return recipe_code, 0
