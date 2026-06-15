from __future__ import annotations

from pathlib import Path

from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_layout import _balanced_wrap_paragraph, _ensure_qt_application
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore
from PySide6.QtGui import QFont


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
    assert len(first[0].roles[0].rendered_lines) == 3
    assert first[0].roles[0].font_file == fonts_root / "THSarabun.ttf"
    assert first[0].roles[0].font_resolution_mode == "workspace_primary"
    assert first[0].roles[0].text_block_width_px > 0
    assert first[0].roles[0].position == "top"
    assert first[0].roles[0].safe_top_ratio == 0.14
    assert first[0].roles[0].safe_bottom_ratio == 0.46
    assert first[0].roles[1].role == "sub"
    assert first[0].roles[1].position == "bottom"
    assert first[0].roles[1].safe_top_ratio == 0.64
    assert first[0].roles[1].safe_bottom_ratio == 0.88


def test_caption_runtime_places_default_main_and_sub_in_separate_safe_bands(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_safe_bands"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = _write_caption_contract(product_dir)
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_safe_bands", source_file=caption_file)
    service = CaptionRuntimeService(metadata_store=store, fonts_root=fonts_root)
    segments = (
        TimelineSegment(
            recipe_id=1,
            segment_type="hook",
            sequence_index=1,
            start_sec=0.0,
            end_sec=4.0,
            target_duration_sec=4.0,
        ),
    )

    resolved = service.resolve_for_segments(
        product_code="product_safe_bands",
        recipe_code="product_safe_bands_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    main_role, sub_role = resolved[0].roles

    assert main_role.box_top_px < 650
    assert sub_role.box_top_px > 1100
    assert main_role.box_top_px < sub_role.box_top_px


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
    assert role.truncated_for_runtime is False
    assert role.fit_strategy in {"scaled_to_fit", "manual_breaks", "wrapped"}
    assert role.line_widths_px
    assert role.box_width_px >= role.text_block_width_px


def test_caption_runtime_supports_point_sized_fonts_and_pixel_layout(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_pt"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["hello world from point size"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                "font_size = 18",
                'font_size_unit = "pt"',
                "min_font_size = 14",
                "max_lines = 4",
                "max_chars_per_line = 18",
                "max_width_ratio = 0.7",
                "line_spacing_ratio = 0.2",
                'alignment = "right"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_pt", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_pt",
        recipe_code="product_pt_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.font_size_unit == "pt"
    assert role.font_size == 24
    assert role.box_width_px == 756
    assert role.max_text_width_px == 716
    assert role.line_left_positions_px
    assert role.line_top_positions_px


def test_caption_runtime_centers_main_within_safe_band_not_full_frame(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_center_band"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["one\\ntwo\\nthree"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'position = "center"',
                "font_size = 72",
                "min_font_size = 48",
                "max_lines = 3",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_center_band", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_center_band",
        recipe_code="product_center_band_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.position == "center"
    assert role.box_top_px < 700


def test_caption_runtime_resolves_centered_textbox_with_left_aligned_text(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_textbox"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["hello world"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "left"',
                'textbox_alignment = "center"',
                "textbox_width_ratio = 0.8",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 48",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_textbox", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_textbox",
        recipe_code="product_textbox_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.textbox_alignment == "center"
    assert role.textbox_width_ratio == 0.8
    assert role.box_width_px == 864
    assert role.box_left_px == 108
    assert role.line_left_positions_px[0] == role.box_left_px + role.padding
    assert role.max_text_width_px == 816


def test_caption_runtime_supports_vertical_alignment_inside_tall_textbox(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_vertical_align"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["one\\ntwo"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'textbox_alignment = "center"',
                'vertical_alignment = "middle"',
                "textbox_width_ratio = 0.6",
                "textbox_height_ratio = 0.2",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 48",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_vertical_align", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_vertical_align",
        recipe_code="product_vertical_align_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.vertical_alignment == "middle"
    assert role.box_height_px == 384
    assert role.line_top_positions_px[0] > role.box_top_px + role.padding
    content_area_bottom = role.box_top_px + role.box_height_px - role.padding
    last_line_bottom = role.line_top_positions_px[-1] + role.line_heights_px[-1]
    assert last_line_bottom < content_area_bottom


def test_caption_runtime_bestfits_long_line_within_narrow_textbox(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_bestfit"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["This line should shrink to fit the box width"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                "textbox_width_ratio = 0.35",
                "padding = 20",
                "font_size = 72",
                "min_font_size = 24",
                "max_lines = 4",
                'overflow_policy = "wrap_then_scale_then_review"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_bestfit", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_bestfit",
        recipe_code="product_bestfit_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.box_width_px == 378
    assert role.max_text_width_px == 338
    assert all(width <= role.max_text_width_px for width in role.line_widths_px)
    assert role.font_size <= role.requested_font_size
    assert role.overflowed is False


def test_caption_runtime_scales_to_fit_fixed_textbox_height(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_height_fit"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["one\\ntwo\\nthree\\nfour"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'vertical_alignment = "middle"',
                "textbox_width_ratio = 0.7",
                "textbox_height_ratio = 0.12",
                "padding = 20",
                "font_size = 96",
                "min_font_size = 24",
                "max_lines = 4",
                'overflow_policy = "wrap_then_scale_then_review"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_height_fit", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_height_fit",
        recipe_code="product_height_fit_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.box_height_px == 230
    assert role.font_size < role.requested_font_size
    assert role.overflowed is False
    assert role.text_block_height_px <= role.box_height_px - (role.padding * 2)


def test_caption_runtime_keeps_overflow_truth_when_textbox_height_cannot_fit(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_height_overflow"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["one\\ntwo\\nthree\\nfour\\nfive"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'vertical_alignment = "middle"',
                "textbox_width_ratio = 0.7",
                "textbox_height_ratio = 0.08",
                "padding = 20",
                "font_size = 88",
                "min_font_size = 48",
                "max_lines = 5",
                'overflow_policy = "wrap_then_scale_then_review"',
                "review_required_if_overflow = true",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_height_overflow", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_height_overflow",
        recipe_code="product_height_overflow_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.box_height_px == 154
    assert role.overflowed is True
    assert role.review_required is True
    assert role.text_block_height_px > role.box_height_px - (role.padding * 2)


def test_caption_runtime_can_right_align_textbox_while_centering_text_inside_it(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_textbox_right"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["fit\\ninside box"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'textbox_alignment = "right"',
                "textbox_width_ratio = 0.5",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 48",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_textbox_right", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_textbox_right",
        recipe_code="product_textbox_right_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.textbox_alignment == "right"
    assert role.box_width_px == 540
    assert role.box_left_px == 540
    assert role.line_left_positions_px[0] > role.box_left_px + role.padding
    assert role.line_left_positions_px[0] < role.box_left_px + role.max_text_width_px


def test_caption_runtime_scales_manual_break_lines_independently_to_fit_width(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_line_scale"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = _write_caption_contract(
        product_dir,
        main_entries=("wow\\nthis is a much longer line than wow\\nspace",),
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_line_scale", source_file=caption_file)
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

    resolved = service.resolve_for_segments(
        product_code="product_line_scale",
        recipe_code="product_line_scale_batch_001",
        segments=segments,
        frame_width_px=360,
        frame_height_px=640,
    )
    role = resolved[0].roles[0]

    assert role.line_break_mode == "manual"
    assert role.fit_strategy == "per_line_scaled_to_fit"
    assert len(role.line_font_sizes_px) == 3
    assert len(set(role.line_font_sizes_px)) > 1
    assert min(role.line_font_sizes_px) == role.min_font_size
    assert role.overflowed is True


def test_balanced_wrap_rearranges_space_separated_lines_more_evenly() -> None:
    _ensure_qt_application()
    font = QFont("Arial")
    font.setPixelSize(40)

    balanced = _balanced_wrap_paragraph(
        "take care of bones and joints every active day",
        font=font,
        max_width_px=500,
        target_line_count=4,
    )

    assert balanced == ("take care", "of bones and", "joints every", "active day")


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
