from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import tomllib

from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_layout import CaptionFrameContext, resolve_caption_layout


class CaptionContractError(ValueError):
    """Raised when a product caption contract is invalid."""


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
    padding: int
    max_lines: int
    max_chars_per_line: int
    max_width_ratio: float
    textbox_width_ratio: float
    textbox_height_ratio: float
    line_spacing_ratio: float
    safe_top_ratio: float
    safe_bottom_ratio: float
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
    text_color: str
    stroke_color: str
    stroke_width: int
    background_color: str | None
    background_opacity: float
    padding: int
    max_lines: int
    max_chars_per_line: int
    max_width_ratio: float
    textbox_width_ratio: float
    textbox_height_ratio: float
    line_spacing_ratio: float
    safe_top_ratio: float
    safe_bottom_ratio: float
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
            max_chars_per_line=style.max_chars_per_line,
            textbox_mode=style.textbox_mode,
            textbox_width_ratio=style.textbox_width_ratio,
            textbox_height_ratio=style.textbox_height_ratio,
            textbox_alignment=style.textbox_alignment,
            line_spacing_ratio=style.line_spacing_ratio,
            padding=style.padding,
            alignment=style.alignment,
            vertical_alignment=style.vertical_alignment,
            position=style.position,
            stroke_width=style.stroke_width,
            safe_top_ratio=style.safe_top_ratio,
            safe_bottom_ratio=style.safe_bottom_ratio,
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
            text_color=style.text_color,
            stroke_color=style.stroke_color,
            stroke_width=style.stroke_width,
            background_color=style.background_color,
            background_opacity=style.background_opacity,
            padding=style.padding,
            max_lines=style.max_lines,
            max_chars_per_line=style.max_chars_per_line,
            max_width_ratio=style.max_width_ratio,
            textbox_width_ratio=style.textbox_width_ratio,
            textbox_height_ratio=style.textbox_height_ratio,
            line_spacing_ratio=style.line_spacing_ratio,
            safe_top_ratio=style.safe_top_ratio,
            safe_bottom_ratio=style.safe_bottom_ratio,
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
    textbox_width_ratio = _bounded_float(
        section.get("textbox_width_ratio", section.get("max_width_ratio")),
        default=default_max_width,
        minimum=0.1,
        maximum=1.0,
        context=f"[caption_properties.{role}].textbox_width_ratio",
    )
    textbox_mode = _choice_text(
        section.get("textbox_mode"),
        default="grouped",
        allowed=("grouped", "per_line"),
        context=f"[caption_properties.{role}].textbox_mode",
    )
    return CaptionRoleStyle(
        position=_optional_text(section.get("position")) or default_position,
        alignment=_optional_text(section.get("alignment")) or "center",
        vertical_alignment=_optional_text(section.get("vertical_alignment")) or "top",
        textbox_alignment=_optional_text(section.get("textbox_alignment")) or "center",
        textbox_mode=textbox_mode,
        font_family=_optional_text(section.get("font_family")) or "Arial",
        font_fallbacks=_text_list(section.get("font_fallbacks"), context=f"[caption_properties.{role}].font_fallbacks"),
        font_size=_positive_int(section.get("font_size"), default=default_font_size, context=f"[caption_properties.{role}].font_size"),
        font_size_unit=_optional_text(section.get("font_size_unit")) or "px",
        min_font_size=_positive_int(
            section.get("min_font_size"),
            default=default_min_font_size,
            context=f"[caption_properties.{role}].min_font_size",
        ),
        font_weight=_optional_text(section.get("font_weight")) or ("bold" if role == "main" else "medium"),
        text_color=_optional_text(section.get("text_color")) or "#FFFFFF",
        stroke_color=_optional_text(section.get("stroke_color")) or "#000000",
        stroke_width=_non_negative_int(
            section.get("stroke_width"),
            default=3 if role == "main" else 2,
            context=f"[caption_properties.{role}].stroke_width",
        ),
        background_color=_optional_text(section.get("background_color")),
        background_opacity=_bounded_float(
            section.get("background_opacity"),
            default=0.15 if role == "main" else 0.30,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].background_opacity",
        ),
        padding=_non_negative_int(section.get("padding"), default=default_padding, context=f"[caption_properties.{role}].padding"),
        max_lines=_positive_int(section.get("max_lines"), default=default_max_lines, context=f"[caption_properties.{role}].max_lines"),
        max_chars_per_line=_positive_int(
            section.get("max_chars_per_line"),
            default=default_max_chars,
            context=f"[caption_properties.{role}].max_chars_per_line",
        ),
        max_width_ratio=_bounded_float(
            section.get("max_width_ratio"),
            default=default_max_width,
            minimum=0.1,
            maximum=1.0,
            context=f"[caption_properties.{role}].max_width_ratio",
        ),
        textbox_width_ratio=textbox_width_ratio,
        textbox_height_ratio=_bounded_float(
            section.get("textbox_height_ratio"),
            default=0.0,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].textbox_height_ratio",
        ),
        line_spacing_ratio=_bounded_float(
            section.get("line_spacing_ratio"),
            default=0.12 if role == "main" else 0.16,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].line_spacing_ratio",
        ),
        safe_top_ratio=_bounded_float(
            section.get("safe_top_ratio"),
            default=default_safe_top,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].safe_top_ratio",
        ),
        safe_bottom_ratio=_bounded_float(
            section.get("safe_bottom_ratio"),
            default=default_safe_bottom,
            minimum=0.0,
            maximum=1.0,
            context=f"[caption_properties.{role}].safe_bottom_ratio",
        ),
        overflow_policy=_optional_text(section.get("overflow_policy")) or default_overflow_policy,
        enter_animation=_optional_text(section.get("enter_animation")) or default_animation,
        review_required_if_overflow=_boolean(
            section.get("review_required_if_overflow"),
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
    seed_key = "|".join(
        (
            seed_scope,
            product_code,
            recipe_code,
            segment.segment_type,
            str(segment.sequence_index),
            role,
        )
    )
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    selection_index = int.from_bytes(digest[:8], "big") % option_count
    return selection_index, seed_key


def _resolve_font(
    *,
    fonts_root: Path,
    font_family: str,
    fallbacks: tuple[str, ...],
) -> tuple[Path | None, str, str]:
    for requested_name, resolution_mode in ((font_family, "workspace_primary"), *[(item, "workspace_fallback") for item in fallbacks]):
        resolved_file = _find_font_file(fonts_root, requested_name)
        if resolved_file is not None:
            return resolved_file, requested_name, resolution_mode
    if fallbacks:
        return None, fallbacks[0], "system_fallback"
    return None, font_family, "system_primary"


def _find_font_file(fonts_root: Path, requested_name: str) -> Path | None:
    if not fonts_root.exists():
        return None
    requested = _normalize_font_name(requested_name)
    if not requested:
        return None
    direct_matches: list[Path] = []
    loose_matches: list[Path] = []
    for file_path in sorted(path for path in fonts_root.iterdir() if path.is_file() and path.suffix.lower() in {".ttf", ".otf"}):
        candidate = _normalize_font_name(file_path.stem)
        if candidate == requested:
            direct_matches.append(file_path)
        elif requested in candidate or candidate in requested:
            loose_matches.append(file_path)
    if direct_matches:
        return direct_matches[0]
    if loose_matches:
        return loose_matches[0]
    return None


def _normalize_font_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _text_list(value, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaptionContractError(f"Expected text list for {context}.")
    result: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text is None:
            continue
        result.append(text)
    return tuple(result)


def _optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_int(value, *, default: int, context: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected positive integer for {context}.") from exc
    if parsed <= 0:
        raise CaptionContractError(f"Expected positive integer for {context}.")
    return parsed


def _non_negative_int(value, *, default: int, context: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected non-negative integer for {context}.") from exc
    if parsed < 0:
        raise CaptionContractError(f"Expected non-negative integer for {context}.")
    return parsed


def _bounded_float(value, *, default: float, minimum: float, maximum: float, context: str) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected numeric value for {context}.") from exc
    if parsed < minimum or parsed > maximum:
        raise CaptionContractError(f"Expected {context} to stay within {minimum}..{maximum}.")
    return parsed


def _choice_text(value, *, default: str, allowed: tuple[str, ...], context: str) -> str:
    if value is None:
        return default
    text = _optional_text(value)
    if text is None:
        return default
    normalized = text.casefold()
    if normalized not in allowed:
        raise CaptionContractError(f"Expected {context} to be one of: {', '.join(allowed)}.")
    return normalized


def _boolean(value, *, default: bool, context: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise CaptionContractError(f"Expected boolean for {context}.")


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
