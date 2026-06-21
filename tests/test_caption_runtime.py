from __future__ import annotations

from pathlib import Path
import pytest
from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_layout import _balanced_wrap_paragraph, _ensure_qt_application
from mt_clip_factory.factory.caption_style_presets import caption_style_preset_group_names, caption_style_preset_names
from mt_clip_factory.factory.caption_runtime import CaptionContractError, CaptionRuntimeService, ProductAutomationMetadataStore
from PySide6.QtGui import QFont, QFontMetricsF


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
    assert first[0].roles[0].max_safe_band_height_ratio == 0.18
    assert first[0].roles[0].effective_safe_bottom_ratio == 0.32
    assert first[0].roles[1].role == "sub"
    assert first[0].roles[1].position == "bottom"
    assert first[0].roles[1].safe_top_ratio == 0.64
    assert first[0].roles[1].safe_bottom_ratio == 0.88
    assert first[0].roles[1].max_safe_band_height_ratio == 0.0


def test_caption_runtime_batch_seed_scope_cycles_caption_choices_across_outputs(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_batch_cycle"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_selection]",
                'mode = "random_with_seed"',
                'seed_scope = "batch"',
                "",
                "[caption_pools.hook]",
                'main = ["hook one", "hook two", "hook three"]',
                'sub = ["sub one", "sub two", "sub three"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                "",
                "[caption_properties.sub]",
                'font_family = "THSarabun"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_batch_cycle", source_file=caption_file)
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

    first = service.resolve_for_segments(
        product_code="product_batch_cycle",
        recipe_code="product_batch_cycle_launch_batch_001",
        segments=segments,
    )
    second = service.resolve_for_segments(
        product_code="product_batch_cycle",
        recipe_code="product_batch_cycle_launch_batch_002",
        segments=segments,
    )
    third = service.resolve_for_segments(
        product_code="product_batch_cycle",
        recipe_code="product_batch_cycle_launch_batch_003",
        segments=segments,
    )
    repeated_first = service.resolve_for_segments(
        product_code="product_batch_cycle",
        recipe_code="product_batch_cycle_launch_batch_001",
        segments=segments,
    )

    assert first[0].roles[0].source_text != second[0].roles[0].source_text
    assert second[0].roles[0].source_text != third[0].roles[0].source_text
    assert {first[0].roles[0].source_text, second[0].roles[0].source_text, third[0].roles[0].source_text} == {
        "hook one",
        "hook two",
        "hook three",
    }
    assert {first[0].roles[1].source_text, second[0].roles[1].source_text, third[0].roles[1].source_text} == {
        "sub one",
        "sub two",
        "sub three",
    }
    assert repeated_first[0].roles[0].source_text == first[0].roles[0].source_text
    assert repeated_first[0].roles[1].source_text == first[0].roles[1].source_text


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
    assert role.fit_strategy in {"scaled_to_fit", "manual_breaks", "single_line", "single_line_best_fit"}
    assert role.line_widths_px
    assert role.text_block_width_px > role.max_text_width_px


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
    assert role.font_size >= 24
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
                "max_safe_band_height_ratio = 0.0",
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
                'textbox_height_mode = "fixed"',
                "textbox_width_ratio = 0.6",
                "textbox_height_ratio = 0.2",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 48",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
                "max_safe_band_height_ratio = 0.0",
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
    assert role.line_top_positions_px[0] >= role.box_top_px + role.padding
    content_area_bottom = role.box_top_px + role.box_height_px - role.padding
    last_line_bottom = role.line_top_positions_px[-1] + role.line_heights_px[-1]
    assert last_line_bottom <= content_area_bottom


def test_caption_runtime_defaults_grouped_textbox_to_content_hug_height(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_content_hug"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["sale now"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'textbox_alignment = "center"',
                "textbox_width_ratio = 0.7",
                "textbox_height_ratio = 0.2",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 48",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_content_hug", source_file=caption_file)
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
        product_code="product_content_hug",
        recipe_code="product_content_hug_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.textbox_height_mode == "content_hug"
    assert role.box_height_px == role.text_block_height_px + (role.padding * 2)
    assert role.box_height_px < 384
    assert role.overflowed is False


def test_caption_runtime_applies_sale_blast_style_preset_defaults(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Baijam.ttf").write_bytes(b"font")
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_preset_defaults"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["sale now"]',
                'sub = ["today only"]',
                "",
                "[caption_properties.main]",
                'style_preset = "sale_blast"',
                "",
                "[caption_properties.sub]",
                'style_preset = "sale_blast"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_preset_defaults", source_file=caption_file)
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
        product_code="product_preset_defaults",
        recipe_code="product_preset_defaults_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    main_role, sub_role = resolved[0].roles

    assert main_role.style_preset == "sale_blast"
    assert main_role.font_family == "TH Baijam"
    assert main_role.textbox_height_mode == "content_hug"
    assert main_role.background_color == "#D61F3A"
    assert main_role.background_opacity == 0.24
    assert main_role.box_border_color == "#FFD447"
    assert main_role.box_border_width == 4
    assert main_role.textbox_width_ratio == 0.74
    assert main_role.max_safe_band_height_ratio == 0.18
    assert main_role.safe_bottom_ratio == 0.32
    assert main_role.effective_safe_bottom_ratio == 0.26
    assert sub_role.style_preset == "sale_blast"
    assert sub_role.font_family == "TH Baijam"
    assert sub_role.background_color == "#111827"
    assert sub_role.box_border_color == "#F8FAFC"
    assert sub_role.position == "bottom"


def test_caption_style_preset_catalog_supports_groups_and_role_filters() -> None:
    assert caption_style_preset_group_names() == ("headline_main", "support_sub", "proof_info")
    assert caption_style_preset_names(role="sub", group_name="support_sub") == ("clean_cta", "dark_lower_third")
    assert caption_style_preset_names(role="main", group_name="support_sub") == ("clean_cta",)


def test_caption_runtime_applies_dark_lower_third_sub_preset_defaults(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Baijam.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_dark_lower_third"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'sub = ["today only"]',
                "",
                "[caption_properties.sub]",
                'style_preset = "dark_lower_third"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_dark_lower_third", source_file=caption_file)
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
        product_code="product_dark_lower_third",
        recipe_code="product_dark_lower_third_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.role == "sub"
    assert role.style_preset == "dark_lower_third"
    assert role.background_color == "#0F172A"
    assert role.background_opacity == 0.64
    assert role.stroke_color == "#020617"
    assert role.textbox_width_ratio == 0.94


def test_caption_runtime_allows_explicit_override_over_style_preset(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Baijam.ttf").write_bytes(b"font")
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_preset_override"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["benefit line"]',
                "",
                "[caption_properties.main]",
                'style_preset = "benefit_stack"',
                'alignment = "right"',
                'textbox_mode = "grouped"',
                'background_color = "#222222"',
                'padding = 12',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_preset_override", source_file=caption_file)
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
        product_code="product_preset_override",
        recipe_code="product_preset_override_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.style_preset == "benefit_stack"
    assert role.alignment == "right"
    assert role.textbox_mode == "grouped"
    assert role.background_color == "#222222"
    assert role.box_border_color == "#CCFBF1"
    assert role.box_border_width == 3
    assert role.padding == 12


def test_caption_runtime_rejects_unknown_style_preset(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    product_dir = tmp_path / "product_bad_preset"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["sale now"]',
                "",
                "[caption_properties.main]",
                'style_preset = "unknown_preset"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_bad_preset", source_file=caption_file)
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

    try:
        service.resolve_for_segments(
            product_code="product_bad_preset",
            recipe_code="product_bad_preset_batch_001",
            segments=segments,
        )
    except CaptionContractError as exc:
        assert "Unknown caption style preset" in str(exc)
    else:
        raise AssertionError("Expected invalid caption style preset to raise CaptionContractError.")


def test_caption_runtime_can_resolve_per_line_textboxes(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_per_line_boxes"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["wow\\namazing offer\\nbuy now"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                'textbox_alignment = "center"',
                'textbox_mode = "per_line"',
                'vertical_alignment = "middle"',
                "textbox_width_ratio = 0.7",
                "textbox_height_ratio = 0.18",
                "padding = 20",
                "font_size = 72",
                "min_font_size = 36",
                "safe_top_ratio = 0.14",
                "safe_bottom_ratio = 0.46",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_per_line_boxes", source_file=caption_file)
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
        product_code="product_per_line_boxes",
        recipe_code="product_per_line_boxes_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.textbox_mode == "per_line"
    assert len(role.line_box_left_positions_px) == 3
    assert len(role.line_box_widths_px) == 3
    assert role.line_box_widths_px[0] < role.line_box_widths_px[1]
    assert role.line_box_widths_px[0] < role.line_box_widths_px[2]
    assert role.line_box_left_positions_px[1] < role.line_box_left_positions_px[0]
    assert role.line_box_left_positions_px[2] < role.line_box_left_positions_px[0]
    assert role.line_box_top_positions_px[1] > role.line_box_top_positions_px[0]


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
                'main = ["Shrink this line to fit"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                "textbox_width_ratio = 0.35",
                "padding = 20",
                "font_size = 72",
                "min_font_size = 8",
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
    assert role.line_break_mode == "single_line"
    assert len(role.rendered_lines) == 1
    assert all(width <= role.max_text_width_px for width in role.line_widths_px)
    assert role.font_size <= role.requested_font_size
    assert role.overflowed is False


def test_caption_runtime_upscales_short_single_line_to_better_fill_textbox_width(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    product_dir = tmp_path / "product_single_line_fill"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["SALE"]',
                "",
                "[caption_properties.main]",
                'font_family = "Arial"',
                'alignment = "center"',
                "textbox_width_ratio = 0.8",
                "padding = 24",
                "font_size = 72",
                "min_font_size = 36",
                "max_lines = 1",
                'overflow_policy = "wrap_then_scale_then_review"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_single_line_fill", source_file=caption_file)
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
        product_code="product_single_line_fill",
        recipe_code="product_single_line_fill_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.line_break_mode == "single_line"
    assert role.fit_strategy == "single_line_best_fit"
    assert role.font_size > role.requested_font_size
    assert role.line_widths_px[0] >= round(role.max_text_width_px * 0.93)
    assert role.line_widths_px[0] <= role.max_text_width_px
    assert role.overflowed is False


def test_caption_runtime_requires_explicit_breaks_before_rendering_multiple_lines(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_explicit_breaks_only"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["Keep one line only without explicit breaks"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'alignment = "center"',
                "textbox_width_ratio = 0.45",
                "padding = 20",
                "font_size = 72",
                "min_font_size = 8",
                "max_lines = 4",
                'overflow_policy = "wrap_then_scale_then_review"',
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_explicit_breaks_only", source_file=caption_file)
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
        product_code="product_explicit_breaks_only",
        recipe_code="product_explicit_breaks_only_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.line_break_mode == "single_line"
    assert role.fit_strategy == "scaled_to_fit"
    assert len(role.rendered_lines) == 1
    assert "\n" not in role.rendered_text
    assert role.line_widths_px[0] <= role.max_text_width_px


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
                'textbox_height_mode = "fixed"',
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
                'textbox_height_mode = "fixed"',
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
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["wow\\nthis is a much longer line than wow\\nspace"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                'textbox_mode = "per_line"',
                "font_size = 72",
                "min_font_size = 48",
                "max_lines = 3",
                'overflow_policy = "wrap_then_scale_then_review"',
            ]
        ),
        encoding="utf-8",
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
    assert len(set(role.line_heights_px)) > 1
    assert role.line_top_positions_px[1] > role.line_top_positions_px[0]
    assert role.line_top_positions_px[2] > role.line_top_positions_px[1]
    assert min(role.line_font_sizes_px) == role.min_font_size
    assert role.overflowed is True


def test_caption_runtime_raises_thai_grouped_headline_stack_to_script_safe_line_advance(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_headline_compression"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["พร้อมดูแลกระดูก\\nเริ่มต้นวันนี้\\nทันที"]',
                "",
                "[caption_properties.main]",
                'font_family = "TH Chakra Petch"',
                'textbox_mode = "grouped"',
                "font_size = 120",
                "min_font_size = 72",
                "padding = 20",
                "textbox_width_ratio = 0.84",
                "line_spacing_ratio = 0.02",
                "line_advance_ratio = 0.80",
                "preferred_line_count = 2",
                "max_lines = 3",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_headline_compression", source_file=caption_file)
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
        product_code="product_headline_compression",
        recipe_code="product_headline_compression_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]
    deltas = tuple(
        role.line_top_positions_px[index + 1] - role.line_top_positions_px[index]
        for index in range(len(role.line_top_positions_px) - 1)
    )

    assert role.line_advance_ratio == pytest.approx(1.0)
    assert role.line_break_mode == "manual_compacted"
    assert role.textbox_mode == "grouped"
    assert len(set(role.line_font_sizes_px)) == 1
    assert role.fit_strategy in {"manual_breaks", "manual_best_fit", "scaled_to_fit"}
    assert deltas
    assert min(deltas) >= role.line_heights_px[0]
    assert len(role.line_pair_spacing_details) == 1
    assert role.line_pair_spacing_details[0].risk_level == "high"
    assert len(role.rendered_lines) == 2


def test_caption_runtime_keeps_configured_compressed_line_advance_for_latin_grouped_headlines(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_latin_headline_compression"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["special launch\\nstart today\\nkeep going"]',
                "",
                "[caption_properties.main]",
                'font_family = "TH Chakra Petch"',
                'textbox_mode = "grouped"',
                "font_size = 120",
                "min_font_size = 72",
                "padding = 20",
                "textbox_width_ratio = 0.84",
                "line_spacing_ratio = 0.02",
                "line_advance_ratio = 0.80",
                "preferred_line_count = 2",
                "max_lines = 3",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_latin_headline_compression", source_file=caption_file)
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
        product_code="product_latin_headline_compression",
        recipe_code="product_latin_headline_compression_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.line_advance_ratio == pytest.approx(0.80)
    assert role.line_break_mode == "manual_compacted"
    assert role.textbox_mode == "grouped"
    assert len(role.line_pair_spacing_details) == 1
    assert role.line_pair_spacing_details[0].risk_level == "low"
    assert len(role.rendered_lines) == 2


def test_caption_runtime_uses_medium_pair_spacing_floor_when_only_one_side_intrudes_into_gap(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_medium_pair_spacing"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["\u0e01\u0e38\\n\u0e01\u0e32"]',
                "",
                "[caption_properties.main]",
                'font_family = "TH Chakra Petch"',
                'textbox_mode = "grouped"',
                "font_size = 120",
                "min_font_size = 72",
                "padding = 20",
                "textbox_width_ratio = 0.84",
                "line_spacing_ratio = 0.02",
                "line_advance_ratio = 0.80",
                "preferred_line_count = 2",
                "max_lines = 2",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_medium_pair_spacing", source_file=caption_file)
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
        product_code="product_medium_pair_spacing",
        recipe_code="product_medium_pair_spacing_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert role.line_advance_ratio == pytest.approx(0.92)
    assert len(role.line_pair_spacing_details) == 1
    assert role.line_pair_spacing_details[0].risk_level == "medium"
    assert role.line_pair_spacing_details[0].applied_line_advance_ratio == pytest.approx(0.92)


def test_caption_runtime_globally_smooths_middle_gap_inside_four_line_thai_block(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_four_line_global_smoothing"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["\u0e01\u0e38\\n\u0e01\u0e34\\n\u0e01\u0e38\\n\u0e01\u0e34"]',
                "",
                "[caption_properties.main]",
                'font_family = "TH Chakra Petch"',
                'textbox_mode = "grouped"',
                "font_size = 120",
                "min_font_size = 72",
                "padding = 20",
                "textbox_width_ratio = 0.84",
                "line_spacing_ratio = 0.02",
                "line_advance_ratio = 0.80",
                "preferred_line_count = 4",
                "max_lines = 4",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_four_line_global_smoothing", source_file=caption_file)
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
        product_code="product_four_line_global_smoothing",
        recipe_code="product_four_line_global_smoothing_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]

    assert len(role.rendered_lines) == 4
    assert [detail.local_risk_level for detail in role.line_pair_spacing_details] == ["high", "low", "high"]
    assert [detail.risk_level for detail in role.line_pair_spacing_details] == ["high", "medium", "high"]
    assert [detail.applied_line_advance_ratio for detail in role.line_pair_spacing_details] == [
        pytest.approx(1.0),
        pytest.approx(0.92),
        pytest.approx(1.0),
    ]


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

    metrics = QFontMetricsF(font)

    assert " ".join(balanced) == "take care of bones and joints every active day"
    assert 2 <= len(balanced) <= 4
    assert all(line.strip() for line in balanced)
    assert all(metrics.horizontalAdvance(line) <= 500 for line in balanced)


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
