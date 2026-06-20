from __future__ import annotations

import pytest

from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore


def test_caption_runtime_clamps_top_band_height_before_covering_presenter_eye_line(tmp_path) -> None:
    media_root = tmp_path / "media_library"
    fonts_root = tmp_path / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "TH Chakra Petch.ttf").write_bytes(b"font")
    product_dir = tmp_path / "product_face_safe_headline"
    product_dir.mkdir(parents=True, exist_ok=True)
    caption_file = product_dir / "captions.toml"
    caption_file.write_text(
        "\n".join(
            [
                "[caption_pools.hook]",
                'main = ["พร้อมดูแลกระดูก\\nเริ่มต้นวันนี้\\nทำต่อทุกวัน"]',
                "",
                "[caption_properties.main]",
                'font_family = "TH Chakra Petch"',
                'style_preset = "sale_blast"',
                "font_size = 108",
                "min_font_size = 64",
                "padding = 18",
                "textbox_width_ratio = 0.78",
                "max_width_ratio = 0.78",
                "line_advance_ratio = 0.78",
                "safe_top_ratio = 0.05",
                "safe_bottom_ratio = 0.30",
                "max_lines = 3",
                "preferred_line_count = 2",
            ]
        ),
        encoding="utf-8",
    )
    store = ProductAutomationMetadataStore(media_root)
    store.sync_caption_contract(product_code="product_face_safe_headline", source_file=caption_file)
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
        product_code="product_face_safe_headline",
        recipe_code="product_face_safe_headline_batch_001",
        segments=segments,
        frame_width_px=1080,
        frame_height_px=1920,
    )
    role = resolved[0].roles[0]
    effective_bottom_px = round(role.frame_height_px * role.effective_safe_bottom_ratio)

    assert role.max_safe_band_height_ratio == 0.18
    assert role.effective_safe_bottom_ratio == pytest.approx(0.23)
    assert role.box_top_px == round(role.frame_height_px * role.safe_top_ratio)
    assert role.box_top_px + role.box_height_px <= effective_bottom_px
    assert role.font_size < role.requested_font_size
