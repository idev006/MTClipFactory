from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CaptionStylePresetGroup:
    name: str
    label: str
    description: str
    sort_order: int


@dataclass(slots=True, frozen=True)
class CaptionStylePresetDefinition:
    name: str
    group_name: str
    label: str
    description: str
    role_defaults: dict[str, dict[str, object]]


_PRESET_GROUPS: dict[str, CaptionStylePresetGroup] = {
    "headline_main": CaptionStylePresetGroup(
        name="headline_main",
        label="Headline Main",
        description="High-attention headline cards for hook or promo claims.",
        sort_order=10,
    ),
    "support_sub": CaptionStylePresetGroup(
        name="support_sub",
        label="Support Sub",
        description="Readable lower-third and CTA support cards for sub captions.",
        sort_order=20,
    ),
    "proof_info": CaptionStylePresetGroup(
        name="proof_info",
        label="Proof Info",
        description="Benefit, proof, and structured information stacks.",
        sort_order=30,
    ),
}


_STYLE_PRESETS: dict[str, CaptionStylePresetDefinition] = {
    "sale_blast": CaptionStylePresetDefinition(
        name="sale_blast",
        group_name="headline_main",
        label="Sale Blast",
        description="Bold promo card with strong hook contrast and compressed grouped headlines.",
        role_defaults={
            "main": {
                "position": "top",
                "alignment": "center",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 92,
                "min_font_size": 52,
                "font_weight": "bold",
                "text_color": "#FFFFFF",
                "stroke_color": "#1A1A1A",
                "stroke_width": 4,
                "background_color": "#D61F3A",
                "background_opacity": 0.24,
                "box_border_color": "#FFD447",
                "box_border_opacity": 0.98,
                "box_border_width": 4,
                "padding": 24,
                "max_lines": 2,
                "preferred_line_count": 2,
                "max_chars_per_line": 16,
                "textbox_width_ratio": 0.74,
                "textbox_height_ratio": 0.16,
                "line_spacing_ratio": 0.04,
                "line_advance_ratio": 0.72,
                "safe_top_ratio": 0.08,
                "safe_bottom_ratio": 0.32,
                "max_safe_band_height_ratio": 0.18,
                "overflow_policy": "wrap_then_scale_then_review",
                "enter_animation": "pop_in",
                "review_required_if_overflow": True,
            },
            "sub": {
                "position": "bottom",
                "alignment": "center",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 52,
                "min_font_size": 34,
                "font_weight": "bold",
                "text_color": "#FFFFFF",
                "stroke_color": "#111111",
                "stroke_width": 3,
                "background_color": "#111827",
                "background_opacity": 0.78,
                "box_border_color": "#F8FAFC",
                "box_border_opacity": 0.94,
                "box_border_width": 3,
                "padding": 16,
                "max_lines": 2,
                "preferred_line_count": 1,
                "max_chars_per_line": 22,
                "textbox_width_ratio": 0.60,
                "textbox_height_ratio": 0.11,
                "line_spacing_ratio": 0.06,
                "line_advance_ratio": 0.88,
                "safe_top_ratio": 0.62,
                "safe_bottom_ratio": 0.84,
                "overflow_policy": "wrap_then_scale_then_review",
                "enter_animation": "fade_in",
                "review_required_if_overflow": True,
            },
        },
    ),
    "clean_cta": CaptionStylePresetDefinition(
        name="clean_cta",
        group_name="support_sub",
        label="Clean CTA",
        description="Balanced grouped caption card for softer CTA or premium messaging.",
        role_defaults={
            "main": {
                "position": "center",
                "alignment": "center",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 72,
                "min_font_size": 40,
                "font_weight": "bold",
                "text_color": "#FFFFFF",
                "stroke_color": "#0F172A",
                "stroke_width": 3,
                "background_color": "#0F172A",
                "background_opacity": 0.78,
                "box_border_color": "#CBD5E1",
                "box_border_opacity": 0.82,
                "box_border_width": 2,
                "padding": 22,
                "max_lines": 2,
                "preferred_line_count": 2,
                "max_chars_per_line": 22,
                "textbox_width_ratio": 0.68,
                "textbox_height_ratio": 0.16,
                "line_spacing_ratio": 0.12,
                "line_advance_ratio": 0.88,
                "safe_top_ratio": 0.18,
                "safe_bottom_ratio": 0.54,
                "overflow_policy": "wrap_then_scale_then_review",
                "enter_animation": "fade_in",
                "review_required_if_overflow": True,
            },
            "sub": {
                "position": "bottom",
                "alignment": "center",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 36,
                "min_font_size": 24,
                "font_weight": "medium",
                "text_color": "#F8FAFC",
                "stroke_color": "#0F172A",
                "stroke_width": 2,
                "background_color": "#1E293B",
                "background_opacity": 0.72,
                "box_border_color": "#94A3B8",
                "box_border_opacity": 0.78,
                "box_border_width": 2,
                "padding": 14,
                "max_lines": 2,
                "preferred_line_count": 1,
                "max_chars_per_line": 28,
                "textbox_width_ratio": 0.62,
                "textbox_height_ratio": 0.10,
                "line_spacing_ratio": 0.14,
                "line_advance_ratio": 0.94,
                "safe_top_ratio": 0.62,
                "safe_bottom_ratio": 0.86,
                "overflow_policy": "wrap_then_truncate_or_review",
                "enter_animation": "fade_in",
                "review_required_if_overflow": True,
            },
        },
    ),
    "dark_lower_third": CaptionStylePresetDefinition(
        name="dark_lower_third",
        group_name="support_sub",
        label="Dark Lower Third",
        description="High-readability bottom support card with stronger background holdout.",
        role_defaults={
            "sub": {
                "position": "bottom",
                "alignment": "center",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 50,
                "min_font_size": 34,
                "font_weight": "bold",
                "text_color": "#FFFFFF",
                "stroke_color": "#020617",
                "stroke_width": 3,
                "background_color": "#0F172A",
                "background_opacity": 0.64,
                "box_border_color": "#E2E8F0",
                "box_border_opacity": 0.84,
                "box_border_width": 2,
                "padding": 18,
                "max_lines": 2,
                "preferred_line_count": 1,
                "max_chars_per_line": 30,
                "textbox_width_ratio": 0.94,
                "textbox_height_ratio": 0.11,
                "line_spacing_ratio": 0.05,
                "line_advance_ratio": 0.90,
                "safe_top_ratio": 0.78,
                "safe_bottom_ratio": 0.94,
                "overflow_policy": "wrap_then_scale_then_review",
                "enter_animation": "fade_in",
                "review_required_if_overflow": True,
            },
        },
    ),
    "benefit_stack": CaptionStylePresetDefinition(
        name="benefit_stack",
        group_name="proof_info",
        label="Benefit Stack",
        description="Structured benefit presentation with stacked rhythm and support copy.",
        role_defaults={
            "main": {
                "position": "center",
                "alignment": "left",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "per_line",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 72,
                "min_font_size": 40,
                "font_weight": "bold",
                "text_color": "#FFFFFF",
                "stroke_color": "#111827",
                "stroke_width": 3,
                "background_color": "#0F766E",
                "background_opacity": 0.86,
                "box_border_color": "#CCFBF1",
                "box_border_opacity": 0.92,
                "box_border_width": 3,
                "padding": 20,
                "max_lines": 4,
                "preferred_line_count": 3,
                "max_chars_per_line": 18,
                "textbox_width_ratio": 0.74,
                "textbox_height_ratio": 0.20,
                "line_spacing_ratio": 0.12,
                "line_advance_ratio": 1.0,
                "safe_top_ratio": 0.14,
                "safe_bottom_ratio": 0.50,
                "overflow_policy": "wrap_then_scale_then_review",
                "enter_animation": "pop_in",
                "review_required_if_overflow": True,
            },
            "sub": {
                "position": "bottom",
                "alignment": "left",
                "vertical_alignment": "middle",
                "textbox_alignment": "center",
                "textbox_mode": "grouped",
                "textbox_height_mode": "content_hug",
                "font_family": "TH Baijam",
                "font_fallbacks": ["TH Chakra Petch", "THSarabun", "Tahoma", "Arial Unicode MS"],
                "font_size": 34,
                "min_font_size": 22,
                "font_weight": "medium",
                "text_color": "#FFFFFF",
                "stroke_color": "#0F172A",
                "stroke_width": 2,
                "background_color": "#134E4A",
                "background_opacity": 0.82,
                "box_border_color": "#99F6E4",
                "box_border_opacity": 0.84,
                "box_border_width": 2,
                "padding": 16,
                "max_lines": 3,
                "preferred_line_count": 1,
                "max_chars_per_line": 28,
                "textbox_width_ratio": 0.70,
                "textbox_height_ratio": 0.12,
                "line_spacing_ratio": 0.14,
                "line_advance_ratio": 0.96,
                "safe_top_ratio": 0.62,
                "safe_bottom_ratio": 0.88,
                "overflow_policy": "wrap_then_truncate_or_review",
                "enter_animation": "fade_in",
                "review_required_if_overflow": True,
            },
        },
    ),
}


def caption_style_preset_group_names() -> tuple[str, ...]:
    return tuple(group.name for group in _sorted_groups())


def caption_style_preset_groups() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "name": group.name,
            "label": group.label,
            "description": group.description,
            "sort_order": group.sort_order,
        }
        for group in _sorted_groups()
    )


def caption_style_preset_names(*, role: str | None = None, group_name: str | None = None) -> tuple[str, ...]:
    return tuple(item["name"] for item in caption_style_preset_catalog(role=role, group_name=group_name))


def caption_style_preset_catalog(
    *,
    role: str | None = None,
    group_name: str | None = None,
) -> tuple[dict[str, object], ...]:
    normalized_role = None if role is None else role.strip().casefold()
    normalized_group = None if group_name is None else group_name.strip().casefold()
    catalog: list[dict[str, object]] = []
    for preset in _sorted_presets():
        if normalized_group is not None and preset.group_name != normalized_group:
            continue
        available_roles = tuple(sorted(preset.role_defaults))
        if normalized_role is not None and normalized_role not in preset.role_defaults:
            continue
        group = _PRESET_GROUPS[preset.group_name]
        catalog.append(
            {
                "name": preset.name,
                "label": preset.label,
                "description": preset.description,
                "group_name": preset.group_name,
                "group_label": group.label,
                "available_roles": available_roles,
            }
        )
    return tuple(catalog)


def resolve_caption_style_preset(*, preset_name: str, role: str) -> dict[str, object]:
    normalized_preset = preset_name.strip().casefold()
    normalized_role = role.strip().casefold()
    preset = _STYLE_PRESETS.get(normalized_preset)
    if preset is None:
        raise ValueError(f"Unknown caption style preset: {preset_name}")
    role_defaults = preset.role_defaults.get(normalized_role)
    if role_defaults is None:
        raise ValueError(f"Caption style preset {preset_name} does not define role {role}.")
    return dict(role_defaults)


def _sorted_groups() -> tuple[CaptionStylePresetGroup, ...]:
    return tuple(sorted(_PRESET_GROUPS.values(), key=lambda item: (item.sort_order, item.name)))


def _sorted_presets() -> tuple[CaptionStylePresetDefinition, ...]:
    return tuple(
        sorted(
            _STYLE_PRESETS.values(),
            key=lambda item: (
                _PRESET_GROUPS[item.group_name].sort_order,
                item.group_name,
                item.name,
            ),
        )
    )
