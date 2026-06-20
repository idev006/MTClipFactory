from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QImage, QPainter, QPen

from mt_clip_factory.factory.caption_layout_support import _build_qfont, _ensure_qt_application
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip


def render_segment_caption_bitmap(*, temp_dir: Path, segment: PreviewSegmentClip) -> Path | None:
    if not segment.captions:
        return None
    frame_width_px = max((role.frame_width_px for role in segment.captions), default=0)
    frame_height_px = max((role.frame_height_px for role in segment.captions), default=0)
    if frame_width_px <= 0 or frame_height_px <= 0:
        return None
    _ensure_qt_application()
    output_path = temp_dir / f"caption_overlay_{segment.sequence_index:02d}.png"
    image = QImage(frame_width_px, frame_height_px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    for role in segment.captions:
        _draw_caption_role(painter, role)
    painter.end()
    image.save(str(output_path))
    return output_path


def _draw_caption_role(painter: QPainter, role) -> None:
    if role.textbox_mode == "per_line":
        for box_left_px, box_top_px, box_width_px, box_height_px in zip(
            role.line_box_left_positions_px,
            role.line_box_top_positions_px,
            role.line_box_widths_px,
            role.line_box_heights_px,
            strict=False,
        ):
            _draw_box(
                painter,
                left_px=box_left_px,
                top_px=box_top_px,
                width_px=box_width_px,
                height_px=box_height_px,
                background_color=role.background_color,
                background_opacity=role.background_opacity,
                box_border_color=role.box_border_color,
                box_border_opacity=role.box_border_opacity,
                box_border_width=role.box_border_width,
            )
    else:
        _draw_box(
            painter,
            left_px=role.box_left_px,
            top_px=role.box_top_px,
            width_px=role.box_width_px,
            height_px=role.box_height_px,
            background_color=role.background_color,
            background_opacity=role.background_opacity,
            box_border_color=role.box_border_color,
            box_border_opacity=role.box_border_opacity,
            box_border_width=role.box_border_width,
        )
    for index, line_text in enumerate(role.rendered_lines):
        if not line_text:
            continue
        font_size_px = role.line_font_sizes_px[index] if role.line_font_sizes_px else role.font_size
        line_height_px = role.line_heights_px[index] if role.line_heights_px else role.line_height_px
        _draw_text_line(
            painter,
            text=line_text,
            font_family=role.font_family,
            font_file=role.font_file,
            font_size_px=font_size_px,
            line_left_px=role.line_left_positions_px[index],
            line_top_px=role.line_top_positions_px[index],
            line_height_px=line_height_px,
            frame_width_px=role.frame_width_px,
            text_color=role.text_color,
            stroke_color=role.stroke_color,
            stroke_width=role.stroke_width,
        )


def _draw_box(
    painter: QPainter,
    *,
    left_px: int,
    top_px: int,
    width_px: int,
    height_px: int,
    background_color: str | None,
    background_opacity: float,
    box_border_color: str | None,
    box_border_opacity: float,
    box_border_width: int,
) -> None:
    if width_px <= 0 or height_px <= 0:
        return
    rect = QRectF(left_px, top_px, width_px, height_px)
    painter.save()
    if background_color and background_opacity > 0:
        painter.fillRect(rect, _to_qcolor(background_color, background_opacity))
    if box_border_color and box_border_opacity > 0 and box_border_width > 0:
        pen = QPen(_to_qcolor(box_border_color, box_border_opacity))
        pen.setWidth(max(1, int(box_border_width)))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
    painter.restore()


def _draw_text_line(
    painter: QPainter,
    *,
    text: str,
    font_family: str,
    font_file: Path | None,
    font_size_px: int,
    line_left_px: int,
    line_top_px: int,
    line_height_px: int,
    frame_width_px: int,
    text_color: str,
    stroke_color: str,
    stroke_width: int,
) -> None:
    font = _build_qfont(font_family=font_family, font_file=font_file, pixel_size=font_size_px)
    metrics = QFontMetricsF(font)
    ascent_px = metrics.ascent()
    line_rect_height_px = max(line_height_px + (max(0, stroke_width) * 4), round(metrics.height()) + (max(0, stroke_width) * 4))
    baseline_y = line_top_px + max(0, stroke_width) + ascent_px
    if stroke_width > 0:
        painter.save()
        painter.setFont(font)
        painter.setPen(_to_qcolor(stroke_color, 1.0))
        for dx, dy in _stroke_offsets(stroke_width):
            painter.drawText(
                QRectF(
                    line_left_px + dx,
                    baseline_y + dy - ascent_px,
                    max(1, frame_width_px - line_left_px),
                    line_rect_height_px,
                ),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextDontClip,
                text,
            )
        painter.restore()
    painter.save()
    painter.setFont(font)
    painter.setPen(_to_qcolor(text_color, 1.0))
    painter.drawText(
        QRectF(
            line_left_px,
            baseline_y - ascent_px,
            max(1, frame_width_px - line_left_px),
            line_rect_height_px,
        ),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextDontClip,
        text,
    )
    painter.restore()


def _stroke_offsets(stroke_width: int) -> tuple[tuple[int, int], ...]:
    radius = max(1, int(stroke_width))
    offsets: list[tuple[int, int]] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            if max(abs(dx), abs(dy)) <= radius:
                offsets.append((dx, dy))
    return tuple(offsets)


def _to_qcolor(value: str, opacity: float) -> QColor:
    color = QColor(value)
    color.setAlphaF(max(0.0, min(1.0, opacity)))
    return color
