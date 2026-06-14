from __future__ import annotations

from dataclasses import dataclass
import tomllib

from mt_clip_factory.factory.caption_runtime import ProductAutomationMetadataStore


class ProductAutomationPolicyError(ValueError):
    """Raised when product automation policy is invalid."""


@dataclass(slots=True, frozen=True)
class AssetFillPolicy:
    asset_type: str
    loop_enabled: bool
    shortfall_mode: str


@dataclass(slots=True, frozen=True)
class ProductAutomationFillPolicies:
    voiceover: AssetFillPolicy
    background_music: AssetFillPolicy
    background_video: AssetFillPolicy
    foreground_video: AssetFillPolicy

    def for_asset_type(self, asset_type: str) -> AssetFillPolicy:
        mapping = {
            "voiceover": self.voiceover,
            "background_music": self.background_music,
            "background_video": self.background_video,
            "foreground_video": self.foreground_video,
        }
        return mapping.get(asset_type, default_fill_policies().foreground_video)

    def to_manifest_dict(self) -> dict[str, dict[str, object]]:
        return {
            policy.asset_type: {
                "loop_enabled": policy.loop_enabled,
                "shortfall_mode": policy.shortfall_mode,
            }
            for policy in (
                self.voiceover,
                self.background_music,
                self.background_video,
                self.foreground_video,
            )
        }


def default_fill_policies() -> ProductAutomationFillPolicies:
    return ProductAutomationFillPolicies(
        voiceover=AssetFillPolicy(asset_type="voiceover", loop_enabled=False, shortfall_mode="silence_tail"),
        background_music=AssetFillPolicy(
            asset_type="background_music",
            loop_enabled=True,
            shortfall_mode="loop_to_timeline",
        ),
        background_video=AssetFillPolicy(
            asset_type="background_video",
            loop_enabled=True,
            shortfall_mode="loop_to_segment",
        ),
        foreground_video=AssetFillPolicy(
            asset_type="foreground_video",
            loop_enabled=False,
            shortfall_mode="freeze_last_frame",
        ),
    )


class ProductAutomationPolicyService:
    def __init__(self, *, metadata_store: ProductAutomationMetadataStore) -> None:
        self._metadata_store = metadata_store

    def load_fill_policies(self, product_code: str) -> ProductAutomationFillPolicies:
        raw_text = self._metadata_store.load_pipeline_contract_text(product_code)
        if raw_text is None:
            return default_fill_policies()
        try:
            data = tomllib.loads(raw_text)
        except tomllib.TOMLDecodeError as exc:
            raise ProductAutomationPolicyError(f"Invalid pipeline.toml for {product_code}: {exc}") from exc
        return parse_fill_policies_from_pipeline_data(data, source_name=product_code)


def parse_fill_policies_from_pipeline_data(
    data: dict[str, object],
    *,
    source_name: str,
) -> ProductAutomationFillPolicies:
    defaults = default_fill_policies()
    fill_policy_section = data.get("fill_policy")
    fill_policy_table = {} if fill_policy_section is None else _expect_table(fill_policy_section, section_name="[fill_policy]", source_name=source_name)
    return ProductAutomationFillPolicies(
        voiceover=_parse_policy(
            fill_policy_table.get("voiceover"),
            default=defaults.voiceover,
            allowed_shortfall_modes={"silence_tail", "review_if_short"},
            source_name=source_name,
        ),
        background_music=_parse_policy(
            fill_policy_table.get("background_music"),
            default=defaults.background_music,
            allowed_shortfall_modes={"loop_to_timeline", "silence_tail"},
            source_name=source_name,
        ),
        background_video=_parse_policy(
            fill_policy_table.get("background_video"),
            default=defaults.background_video,
            allowed_shortfall_modes={"loop_to_segment", "freeze_last_frame"},
            source_name=source_name,
        ),
        foreground_video=_parse_policy(
            fill_policy_table.get("foreground_video"),
            default=defaults.foreground_video,
            allowed_shortfall_modes={"freeze_last_frame", "review_if_short", "loop_to_segment"},
            source_name=source_name,
        ),
    )


def _parse_policy(
    value: object,
    *,
    default: AssetFillPolicy,
    allowed_shortfall_modes: set[str],
    source_name: str,
) -> AssetFillPolicy:
    section = {} if value is None else _expect_table(
        value,
        section_name=f"[fill_policy.{default.asset_type}]",
        source_name=source_name,
    )
    loop_enabled = _as_bool(section.get("loop_enabled"), default=default.loop_enabled, context=f"{source_name}:{default.asset_type}.loop_enabled")
    shortfall_mode = _as_text(section.get("shortfall_mode"), default=default.shortfall_mode, context=f"{source_name}:{default.asset_type}.shortfall_mode")
    if shortfall_mode not in allowed_shortfall_modes:
        raise ProductAutomationPolicyError(
            f"Unsupported shortfall_mode '{shortfall_mode}' for {default.asset_type} in {source_name}."
        )
    if shortfall_mode.startswith("loop_to_") and not loop_enabled:
        raise ProductAutomationPolicyError(
            f"{default.asset_type} in {source_name} cannot request {shortfall_mode} while loop_enabled=false."
        )
    if shortfall_mode in {"freeze_last_frame", "review_if_short", "silence_tail"} and default.asset_type in {"voiceover", "foreground_video"} and loop_enabled and shortfall_mode != "silence_tail":
        raise ProductAutomationPolicyError(
            f"{default.asset_type} in {source_name} cannot keep loop_enabled=true with shortfall_mode={shortfall_mode}."
        )
    return AssetFillPolicy(
        asset_type=default.asset_type,
        loop_enabled=loop_enabled,
        shortfall_mode=shortfall_mode,
    )


def _expect_table(value: object, *, section_name: str, source_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ProductAutomationPolicyError(f"Expected table {section_name} in {source_name}.")
    return value


def _as_bool(value: object, *, default: bool, context: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ProductAutomationPolicyError(f"Expected boolean for {context}.")


def _as_text(value: object, *, default: str, context: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        raise ProductAutomationPolicyError(f"Expected non-empty text for {context}.")
    return text
