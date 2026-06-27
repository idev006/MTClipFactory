from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

from mt_clip_factory.factory.caption_bitmap_overlay import render_segment_caption_bitmap
from mt_clip_factory.factory.caption_runtime import ResolvedCaptionRole
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip


def _build_caption_role(
    *,
    rendered_lines: tuple[str, ...],
    line_left_positions_px: tuple[int, ...],
    line_top_positions_px: tuple[int, ...],
    line_font_sizes_px: tuple[int, ...],
    line_heights_px: tuple[int, ...],
    box_left_px: int,
    box_top_px: int,
    box_width_px: int,
    box_height_px: int,
    line_box_left_positions_px: tuple[int, ...] = (),
    line_box_top_positions_px: tuple[int, ...] = (),
    line_box_widths_px: tuple[int, ...] = (),
    line_box_heights_px: tuple[int, ...] = (),
    textbox_mode: str = "grouped",
    background_color: str | None = "#000000",
    background_opacity: float = 0.15,
    box_border_color: str | None = None,
    box_border_opacity: float = 0.0,
    box_border_width: int = 0,
) -> ResolvedCaptionRole:
    line_count = len(rendered_lines)
    line_widths_px = tuple(220 for _ in rendered_lines)
    return ResolvedCaptionRole(
        role="main",
        source_text="\n".join(rendered_lines),
        rendered_text="\n".join(rendered_lines),
        rendered_lines=rendered_lines,
        segment_type="hook",
        sequence_index=1,
        seed_key="seed",
        selection_index=0,
        line_break_mode="manual",
        fit_strategy="manual_breaks",
        line_count=line_count,
        font_family="Tahoma",
        font_fallbacks=(),
        font_size=72,
        requested_font_size=72,
        font_size_unit="px",
        min_font_size=48,
        font_weight="bold",
        font_source="Tahoma",
        font_file=None,
        font_resolution_mode="system_primary",
        font_resolution_target="Tahoma",
        pool_names=("hook",),
        pool_resolution_mode="segment_default",
        pool_warning=None,
        position="top",
        alignment="left",
        vertical_alignment="top",
        textbox_alignment="center",
        textbox_mode=textbox_mode,
        textbox_height_mode="content_hug",
        style_preset="sale_blast",
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=2,
        background_color=background_color,
        background_opacity=background_opacity,
        box_border_color=box_border_color,
        box_border_opacity=box_border_opacity,
        box_border_width=box_border_width,
        padding=20,
        max_lines=3,
        preferred_line_count=2,
        max_chars_per_line=18,
        max_width_ratio=0.78,
        textbox_width_ratio=0.78,
        textbox_height_ratio=0.0,
        line_spacing_ratio=0.12,
        line_advance_ratio=1.0,
        line_pair_spacing_details=(),
        safe_top_ratio=0.14,
        safe_bottom_ratio=0.46,
        max_safe_band_height_ratio=0.0,
        effective_safe_bottom_ratio=0.46,
        line_spacing_px=8,
        line_font_sizes_px=line_font_sizes_px,
        line_widths_px=line_widths_px,
        line_height_px=line_heights_px[0] if line_heights_px else 72,
        line_heights_px=line_heights_px,
        text_block_width_px=max(line_widths_px, default=0),
        text_block_height_px=sum(line_heights_px),
        max_text_width_px=720,
        line_left_positions_px=line_left_positions_px,
        line_top_positions_px=line_top_positions_px,
        line_box_left_positions_px=line_box_left_positions_px,
        line_box_top_positions_px=line_box_top_positions_px,
        line_box_widths_px=line_box_widths_px,
        line_box_heights_px=line_box_heights_px,
        box_left_px=box_left_px,
        box_top_px=box_top_px,
        box_width_px=box_width_px,
        box_height_px=box_height_px,
        frame_width_px=1080,
        frame_height_px=1920,
        overflow_policy="wrap_then_scale_then_review",
        enter_animation="pop_in",
        overflowed=False,
        review_required=False,
        truncated_for_runtime=False,
    )


def _build_segment(*, role: ResolvedCaptionRole) -> PreviewSegmentClip:
    source_file = Path("placeholder.mp4")
    return PreviewSegmentClip(
        sequence_index=1,
        segment_type="hook",
        layer_name="background_visual",
        asset_id=1,
        asset_code="bg",
        source_file=source_file,
        start_sec=0.0,
        end_sec=1.0,
        target_duration_sec=1.0,
        fill_mode="trim_to_segment",
        captions=(role,),
    )


def _count_nontransparent_pixels(image: QImage, *, left: int, top: int, width: int, height: int) -> int:
    count = 0
    for y in range(top, min(image.height(), top + height)):
        for x in range(left, min(image.width(), left + width)):
            if image.pixelColor(x, y).alpha() > 0:
                count += 1
    return count


def test_render_segment_caption_bitmap_draws_grouped_box_border_and_text(tmp_path) -> None:
    role = _build_caption_role(
        rendered_lines=("limited offer",),
        line_left_positions_px=(180,),
        line_top_positions_px=(420,),
        line_font_sizes_px=(72,),
        line_heights_px=(80,),
        box_left_px=108,
        box_top_px=396,
        box_width_px=864,
        box_height_px=160,
        box_border_color="#FFD447",
        box_border_opacity=0.96,
        box_border_width=4,
    )

    output_path = render_segment_caption_bitmap(temp_dir=tmp_path, segment=_build_segment(role=role))

    assert output_path is not None
    image = QImage(str(output_path))
    assert image.width() == 1080
    assert image.height() == 1920
    assert image.pixelColor(140, 430).alpha() > 0
    assert image.pixelColor(108, 396).red() > 200
    assert image.pixelColor(108, 396).green() > 180
    assert _count_nontransparent_pixels(image, left=170, top=410, width=260, height=90) > 0


def test_render_segment_caption_bitmap_draws_per_line_textboxes(tmp_path) -> None:
    role = _build_caption_role(
        rendered_lines=("wow", "buy now"),
        line_left_positions_px=(300, 260),
        line_top_positions_px=(420, 540),
        line_font_sizes_px=(72, 72),
        line_heights_px=(78, 78),
        box_left_px=182,
        box_top_px=396,
        box_width_px=716,
        box_height_px=320,
        textbox_mode="per_line",
        line_box_left_positions_px=(276, 236),
        line_box_top_positions_px=(396, 516),
        line_box_widths_px=(168, 228),
        line_box_heights_px=(126, 126),
    )

    output_path = render_segment_caption_bitmap(temp_dir=tmp_path, segment=_build_segment(role=role))

    assert output_path is not None
    image = QImage(str(output_path))
    assert _count_nontransparent_pixels(image, left=280, top=400, width=150, height=110) > 0
    assert _count_nontransparent_pixels(image, left=240, top=520, width=210, height=110) > 0
    assert _count_nontransparent_pixels(image, left=640, top=700, width=80, height=80) == 0


def test_render_segment_caption_bitmap_supports_thai_text(tmp_path) -> None:
    role = _build_caption_role(
        rendered_lines=("เริ่มวันนี้", "ทำต่อทุกวัน"),
        line_left_positions_px=(180, 180),
        line_top_positions_px=(420, 540),
        line_font_sizes_px=(72, 72),
        line_heights_px=(86, 86),
        box_left_px=108,
        box_top_px=396,
        box_width_px=864,
        box_height_px=260,
        box_border_color="#FFD447",
        box_border_opacity=0.96,
        box_border_width=4,
    )

    output_path = render_segment_caption_bitmap(temp_dir=tmp_path, segment=_build_segment(role=role))

    assert output_path is not None
    image = QImage(str(output_path))
    assert _count_nontransparent_pixels(image, left=170, top=410, width=320, height=260) > 0
