from __future__ import annotations

from mt_clip_factory.config import default_config


def test_default_config_uses_workspace_relative_defaults(tmp_path) -> None:
    config = default_config(tmp_path)

    assert config.paths.database_path == tmp_path / "ad_kitchen.db"
    assert config.paths.media_root == tmp_path / "media_library"
    assert config.paths.docs_root == tmp_path / "doc"
    assert config.paths.outputs_root == tmp_path / "outputs"
    assert config.paths.preview_root == tmp_path / "outputs" / "preview"


def test_default_config_resolves_configured_paths(tmp_path) -> None:
    config_path = tmp_path / "app_config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'database_path = "data\\\\mtclip.db"',
                'media_root = "storage\\\\media"',
                'docs_root = "docs"',
                'outputs_root = "build\\\\outputs"',
                'preview_root = "build\\\\preview"',
                "",
                "[ffmpeg]",
                'root = "F:\\\\ffmpeg"',
                'ffprobe = "F:\\\\ffmpeg\\\\bin\\\\ffprobe.exe"',
                'ffmpeg = "F:\\\\ffmpeg\\\\bin\\\\ffmpeg.exe"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    config = default_config(tmp_path)

    assert config.paths.database_path == tmp_path / "data" / "mtclip.db"
    assert config.paths.media_root == tmp_path / "storage" / "media"
    assert config.paths.docs_root == tmp_path / "docs"
    assert config.paths.outputs_root == tmp_path / "build" / "outputs"
    assert config.paths.preview_root == tmp_path / "build" / "preview"
    assert str(config.ffmpeg_path).endswith("ffmpeg.exe")
