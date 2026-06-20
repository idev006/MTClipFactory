from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QMessageBox


def open_selected_product_folder(window) -> None:  # noqa: ANN001
    product_dir = resolve_selected_product_dir(window)
    if product_dir is None:
        QMessageBox.information(window, "Auto Factory", "Select one product row first.")
        return
    open_local_path(window, product_dir, description="product folder")


def open_selected_contracts_folder(window) -> None:  # noqa: ANN001
    product_dir = resolve_selected_product_dir(window)
    if product_dir is None:
        QMessageBox.information(window, "Auto Factory", "Select one product row first.")
        return
    contracts_dir = product_dir / "contracts"
    open_local_path(window, contracts_dir if contracts_dir.exists() else product_dir, description="contracts folder")


def open_selected_runs_folder(window) -> None:  # noqa: ANN001
    product_dir = resolve_selected_product_dir(window)
    if product_dir is None:
        QMessageBox.information(window, "Auto Factory", "Select one product row first.")
        return
    batch_code = resolve_selected_batch_code(window)
    preferred_path = product_dir / "runs" / batch_code if batch_code else product_dir / "runs"
    fallback_path = product_dir / "runs"
    if preferred_path.exists():
        open_local_path(window, preferred_path, description="runs folder")
        return
    if fallback_path.exists():
        open_local_path(window, fallback_path, description="runs folder")
        return
    QMessageBox.information(
        window,
        "Auto Factory",
        f"Runs folder does not exist yet.\nExpected path: {preferred_path}",
    )


def copy_selected_product_summary(window) -> None:  # noqa: ANN001
    summary = window.selected_product_text.toPlainText().strip()
    if not summary or summary == window.SELECTED_PRODUCT_PLACEHOLDER:
        QMessageBox.information(window, "Auto Factory", "There is no selected product summary to copy yet.")
        return
    QGuiApplication.clipboard().setText(summary)
    set_feedback_message(window, "Selected product summary copied to clipboard.")


def refresh_selected_product_action_state(window) -> None:  # noqa: ANN001
    has_product_path = resolve_selected_product_dir(window) is not None
    has_summary = bool(window.selected_product_text.toPlainText().strip()) and (
        window.selected_product_text.toPlainText() != window.SELECTED_PRODUCT_PLACEHOLDER
    )
    window.open_product_folder_button.setEnabled(has_product_path)
    window.open_contracts_button.setEnabled(has_product_path)
    window.open_runs_button.setEnabled(has_product_path)
    window.copy_summary_button.setEnabled(has_summary)


def resolve_selected_product_dir(window) -> Path | None:  # noqa: ANN001
    preflight_report = window._view_model.preflight_report
    if preflight_report is not None and hasattr(window, "preflight_products_table"):
        row_index = _selected_row_index(window.preflight_products_table)
        if row_index is not None and row_index < len(preflight_report.product_reports):
            return Path(preflight_report.product_reports[row_index].product_dir)

    run_report = window._view_model.run_report
    if run_report is not None and hasattr(window, "product_reports_table"):
        row_index = _selected_row_index(window.product_reports_table)
        if row_index is not None and row_index < len(run_report.product_reports):
            product_dir = run_report.product_reports[row_index].product_dir
            if product_dir:
                return Path(product_dir)
    return None


def resolve_selected_batch_code(window) -> str | None:  # noqa: ANN001
    run_report = window._view_model.run_report
    if run_report is None or not hasattr(window, "product_reports_table"):
        return None
    row_index = _selected_row_index(window.product_reports_table)
    if row_index is None or row_index >= len(run_report.product_reports):
        return None
    return run_report.batch_code


def open_local_path(window, path: Path, *, description: str) -> None:  # noqa: ANN001
    if not path.exists():
        QMessageBox.information(window, "Auto Factory", f"Cannot open {description} because it does not exist:\n{path}")
        return
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
        QMessageBox.warning(window, "Auto Factory", f"Unable to open {description}:\n{path}")


def set_feedback_message(window, message: str) -> None:  # noqa: ANN001
    set_feedback = getattr(window._view_model, "_set_feedback", None)
    if callable(set_feedback):
        set_feedback(message)
        return
    if hasattr(window._view_model, "feedback"):
        window._view_model.feedback = message
        feedback_changed = getattr(window._view_model, "feedback_changed", None)
        if feedback_changed is not None:
            feedback_changed.emit()
    window._refresh_feedback()


def _selected_row_index(table) -> int | None:  # noqa: ANN001
    selected_items = table.selectedItems()
    if not selected_items:
        return None
    return selected_items[0].row()
