from __future__ import annotations

from pathlib import Path

from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore


def _write_caption_contract(
    product_dir: Path,
    *,
    max_lines: int = 3,
    max_chars_per_line: int = 18,
    main_entries: tuple[str, ...] = ("กลับมาแจก\\nความสดใส\\nและพลังบวกได้เต็มที่", "พลังบวกทุกวัน"),
) -> Path:
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_selection]",
                'mode = "random_with_seed"',
                'seed_scope = "recipe"',
                "",
                "[caption_pools.hook]",
                f"main = [{', '.join(f'\"{entry}\"' for entry in main_entries)}]",
                'sub = ["เริ่มต้นวันใหม่ด้วยพลังที่ใช่"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                "font_size = 72",
                "min_font_size = 48",
                f"max_lines = {max_lines}",
                f"max_chars_per_line = {max_chars_per_line}",
                'overflow_policy = "wrap_then_scale_then_review"',
                "review_required_if_overflow = true",
                "",
                "[caption_properties.sub]",
                'font_family = "THSarabun"',
                "font_size = 40",
                "min_font_size = 30",
                "max_lines = 2",
                "max_chars_per_line = 24",
                'overflow_policy = "wrap_then_truncate_or_review"',
                "review_required_if_overflow = true",
            ]
        ),
        encoding="utf-8",
    )
    return caption_file


def test_caption_runtime_resolves_deterministic_roles_and_workspace_font(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_a"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = _write_caption_contract(
        product_dir,
        main_entries=("กลับมาแจก\\nความสดใส\\nและพลังบวกได้เต็มที่",),
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_a", source_file=caption_file)
    service = CaptionRuntimeService(metadata_store=store, fonts_root=fonts_root)
    segments = (
        TimelineSegment(
            recipe_id=1,
            segment_type="hook",
            sequence_index=1,
            start_sec=0.0,
            end_sec=3.0,
            target_duration_sec=3.0,
        ),
    )

    first = service.resolve_for_segments(product_code="product_a", recipe_code="product_a_batch_001", segments=segments)
    second = service.resolve_for_segments(product_code="product_a", recipe_code="product_a_batch_001", segments=segments)

    assert len(first) == 1
    assert first[0].roles[0].selection_index == second[0].roles[0].selection_index
    assert first[0].roles[0].rendered_text.count("\n") == 2
    assert first[0].roles[0].font_file == fonts_root / "THSarabun.ttf"
    assert first[0].roles[0].font_resolution_mode == "workspace_primary"
    assert first[0].roles[1].role == "sub"


def test_caption_runtime_flags_overflow_for_review(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_b"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = _write_caption_contract(
        product_dir,
        max_lines=1,
        max_chars_per_line=4,
        main_entries=("ข้อความยาวมากจนเกินขอบเขต",),
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_b", source_file=caption_file)
    service = CaptionRuntimeService(metadata_store=store, fonts_root=fonts_root)
    segments = (
        TimelineSegment(
            recipe_id=1,
            segment_type="hook",
            sequence_index=1,
            start_sec=0.0,
            end_sec=3.0,
            target_duration_sec=3.0,
        ),
    )

    resolved = service.resolve_for_segments(product_code="product_b", recipe_code="product_b_batch_001", segments=segments)
    role = resolved[0].roles[0]

    assert role.overflowed is True
    assert role.review_required is True
    assert role.truncated_for_runtime is True
    assert role.fit_strategy == "truncated_for_runtime"


def test_metadata_store_removes_stale_caption_contract_when_source_is_missing(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    product_dir = tmp_path / "product_c"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = _write_caption_contract(product_dir)
    store = ProductAutomationMetadataStore(media_root)

    synced = store.sync_caption_contract(product_code="product_c", source_file=caption_file)
    assert synced is not None and synced.exists()
    removed = store.sync_caption_contract(product_code="product_c", source_file=None)

    assert removed is None
    assert not store.caption_contract_path("product_c").exists()
