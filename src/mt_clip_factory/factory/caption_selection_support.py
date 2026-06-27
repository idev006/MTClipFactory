from __future__ import annotations

from dataclasses import dataclass
import hashlib

from mt_clip_factory.domain.timeline_segments import TimelineSegment


@dataclass(slots=True, frozen=True)
class CaptionSelectionSignature:
    role_texts: tuple[tuple[str, str, str], ...] = ()
    main_role_texts: tuple[tuple[str, str], ...] = ()


def resolve_caption_selection_signature(
    *,
    pools: dict[str, object],
    seed_scope: str,
    product_code: str,
    recipe_code: str,
    segment_types: tuple[str, ...] | None = None,
) -> CaptionSelectionSignature:
    ordered_segment_types = ordered_caption_segment_types(
        configured_segment_types=tuple(pools),
        requested_segment_types=segment_types,
    )
    role_texts: list[tuple[str, str, str]] = []
    main_role_texts: list[tuple[str, str]] = []
    for sequence_index, segment_type in enumerate(ordered_segment_types, start=1):
        pool = pools.get(segment_type)
        if pool is None:
            continue
        segment = TimelineSegment(
            recipe_id=0,
            segment_type=segment_type,
            sequence_index=sequence_index,
            start_sec=float(sequence_index - 1),
            end_sec=float(sequence_index),
            target_duration_sec=1.0,
        )
        main_options = getattr(pool, "main", ())
        if main_options:
            selection_index, _seed_key = select_caption_index(
                option_count=len(main_options),
                product_code=product_code,
                recipe_code=recipe_code,
                segment=segment,
                role="main",
                seed_scope=seed_scope,
            )
            source_text = main_options[selection_index]
            role_texts.append((segment_type, "main", source_text))
            main_role_texts.append((segment_type, source_text))
        sub_options = getattr(pool, "sub", ())
        if sub_options:
            selection_index, _seed_key = select_caption_index(
                option_count=len(sub_options),
                product_code=product_code,
                recipe_code=recipe_code,
                segment=segment,
                role="sub",
                seed_scope=seed_scope,
            )
            role_texts.append((segment_type, "sub", sub_options[selection_index]))
    return CaptionSelectionSignature(
        role_texts=tuple(role_texts),
        main_role_texts=tuple(main_role_texts),
    )


def select_caption_index(
    *,
    option_count: int,
    product_code: str,
    recipe_code: str,
    segment: TimelineSegment,
    role: str,
    seed_scope: str,
) -> tuple[int, str]:
    if option_count <= 0:
        raise ValueError("Caption option count must be greater than zero.")
    normalized_scope = seed_scope.strip().casefold()
    if normalized_scope == "batch":
        batch_seed_key, batch_position = resolve_batch_seed_context(
            product_code=product_code,
            recipe_code=recipe_code,
            segment=segment,
            role=role,
        )
        selection_index = seeded_cycled_index(
            option_count=option_count,
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
    selection_index = seeded_index(option_count=option_count, seed_key=seed_key)
    return selection_index, seed_key


def resolve_batch_seed_context(
    *,
    product_code: str,
    recipe_code: str,
    segment: TimelineSegment,
    role: str,
) -> tuple[str, int]:
    batch_recipe_code, batch_position = split_batch_recipe_code(recipe_code)
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


def split_batch_recipe_code(recipe_code: str) -> tuple[str, int]:
    prefix, separator, suffix = recipe_code.rpartition("_")
    if separator and suffix.isdigit():
        return prefix, max(0, int(suffix) - 1)
    return recipe_code, 0


def ordered_caption_segment_types(
    *,
    configured_segment_types: tuple[str, ...],
    requested_segment_types: tuple[str, ...] | None,
) -> tuple[str, ...]:
    normalized_configured = tuple(segment.casefold() for segment in configured_segment_types)
    normalized_requested = None if requested_segment_types is None else tuple(segment.casefold() for segment in requested_segment_types)
    if normalized_requested is not None:
        return tuple(
            dict.fromkeys(segment for segment in normalized_requested if segment in normalized_configured)
        )
    allowed = set(normalized_configured)
    ordered_known = tuple(segment for segment in ("hook", "problem", "benefit", "proof", "cta") if segment in allowed)
    extra_segments = tuple(sorted(segment for segment in normalized_configured if segment not in ordered_known))
    return ordered_known + extra_segments


def seeded_index(*, option_count: int, seed_key: str) -> int:
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % option_count


def seeded_cycled_index(*, option_count: int, seed_key: str, position: int) -> int:
    if option_count == 1:
        return 0
    digest = hashlib.sha256(seed_key.encode("utf-8")).digest()
    start_index = int.from_bytes(digest[:8], "big") % option_count
    step_options = tuple(step for step in range(1, option_count + 1) if _gcd(step, option_count) == 1)
    step_seed = int.from_bytes(digest[8:16], "big") % len(step_options)
    step = step_options[step_seed]
    return (start_index + (step * max(0, position))) % option_count


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)
