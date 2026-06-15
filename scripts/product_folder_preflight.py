from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = WORKSPACE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mt_clip_factory.bootstrap import build_resource_library_module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit one MTClipFactory product folder or batch root before automation.")
    parser.add_argument("root_folder", help="Product folder or batch root to audit.")
    parser.add_argument("--scan-depth", type=int, default=1, help="Discovery depth for nested product folders.")
    parser.add_argument("--json-out", help="Optional path to write the full preflight report as JSON.")
    return parser


def render_text_report(report) -> str:
    lines: list[str] = []
    lines.append(f"Preflight status: {report.status}")
    lines.append(f"Root folder: {report.root_folder}")
    lines.append(f"Scan depth: {report.scan_depth}")
    lines.append(f"Discovered product folders: {len(report.discovered_product_dirs)}")
    lines.append(f"Errors: {report.error_count}")
    lines.append(f"Warnings: {report.warning_count}")
    for product_report in report.product_reports:
        lines.append("")
        lines.append(
            f"Product: {product_report.product_code or '<unknown>'} | "
            f"status={product_report.status} | layout={product_report.layout_mode} | "
            f"assets={product_report.ingestible_asset_count}"
        )
        lines.append(f"Path: {product_report.product_dir}")
        if product_report.product_name is not None:
            lines.append(f"Name: {product_report.product_name}")
        if product_report.requested_output_count is not None:
            lines.append(f"Requested outputs: {product_report.requested_output_count}")
        for asset_audit in product_report.asset_folders:
            lines.append(
                f"- {asset_audit.folder_name}: files={asset_audit.ingestible_file_count}, "
                f"tags_toml={'yes' if asset_audit.tag_file_present else 'no'}, "
                f"required_matches={asset_audit.matching_required_file_count}"
            )
        if product_report.issues:
            lines.append("Issues:")
            for issue in product_report.issues:
                location = f" [{issue.location}]" if issue.location else ""
                lines.append(f"  - {issue.severity.upper()} {issue.code}: {issue.message}{location}")
    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    for logger_name in ("alembic", "alembic.runtime", "alembic.runtime.migration"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        logger.disabled = True
    module = build_resource_library_module(WORKSPACE_ROOT, run_startup_recovery=False)
    report = module.auto_factory_folder_service.audit_batch_root(
        Path(args.root_folder),
        scan_depth=args.scan_depth,
    )
    print(render_text_report(report))
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report.error_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
