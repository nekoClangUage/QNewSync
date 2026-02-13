from multiprocessing import active_children
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app_settings import AppSettings, RegexRule
from ui import constants as C
from ui.main_window import MainWindow


def create_files(directory: Path, count: int, *, size: int = 1024, prefix: str = "file") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    content = "x" * size
    for i in range(count):
        (directory / f"{prefix}_{i}.dat").write_text(content, encoding="utf-8")


def setup_directory_dialog(monkeypatch, paths: list[str]) -> None:
    iterator = iter(paths)
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: next(iterator),
    )


def wait_for_compare(window: MainWindow, qtbot, timeout: int = 20000) -> None:
    qtbot.waitUntil(lambda: window.compare_thread is not None, timeout=timeout)
    compare_thread = window.compare_thread
    qtbot.waitUntil(lambda: not compare_thread.isRunning(), timeout=timeout)
    qtbot.waitUntil(lambda: window.status_label.text() == C.LABEL_READY_TO_SYNC, timeout=timeout)


def wait_for_thread(qtbot, thread, timeout: int = 20000) -> None:
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=timeout)


def collect_tree_paths(tree) -> set[str]:
    """Collect visible file/dir names from a LazyDirectoryTreeWidget."""
    paths: set[str] = set()
    proxy = tree._proxy_model
    root = tree.rootIndex()

    def walk(parent_index):
        for row in range(proxy.rowCount(parent_index)):
            idx = proxy.index(row, 0, parent_index)
            rel = proxy._get_relative_path(idx)
            if rel:
                paths.add(rel)
            walk(idx)

    walk(root)
    return paths


@pytest.fixture
def message_box_spy(monkeypatch):
    calls = []

    def record(kind):
        def handler(*args, **kwargs):
            calls.append((kind, args, kwargs))
            return QMessageBox.StandardButton.Ok

        return handler

    monkeypatch.setattr(QMessageBox, "information", record("information"))
    monkeypatch.setattr(QMessageBox, "warning", record("warning"))
    monkeypatch.setattr(QMessageBox, "critical", record("critical"))
    return calls


@pytest.fixture
def main_window(qtbot, message_box_spy):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close_application()


def has_message(calls, kind: str, title: str) -> bool:
    return any(call_kind == kind and args[1] == title for call_kind, args, _ in calls)


def test_main_window_compare_sync_integration(qtbot, main_window, monkeypatch, tmp_path, message_box_spy):
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    create_files(dir1, 120, size=2048, prefix="payload")
    dir2.mkdir()

    setup_directory_dialog(monkeypatch, [str(dir1), str(dir2)])

    main_window.select_directory1()
    main_window.select_directory2()
    wait_for_compare(main_window, qtbot, timeout=30000)

    assert main_window.status_label.text() == C.LABEL_READY_TO_SYNC

    main_window.start_synchronization()
    sync_thread = main_window.sync_thread
    wait_for_thread(qtbot, sync_thread, timeout=30000)

    assert len(list(dir2.glob("*.dat"))) == 120
    QApplication.processEvents()
    qtbot.waitUntil(
        lambda: (
            main_window.status_label.text()
            in {
                C.STATUS_SYNC_COMPLETED,
                C.STATUS_SYNC_COMPLETED_HIGHLIGHT,
            }
        ),
        timeout=5000,
    )
    assert main_window.sync_btn.isEnabled()
    assert has_message(message_box_spy, "information", C.DIALOG_SYNC_COMPLETED)


@pytest.mark.slow
def test_main_window_stop_cancel_rollback_stress(qtbot, main_window, monkeypatch, tmp_path, message_box_spy):
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    create_files(dir1, 1200, size=32768, prefix="bulk")
    dir2.mkdir()

    setup_directory_dialog(monkeypatch, [str(dir1), str(dir2)])

    main_window.select_directory1()
    main_window.select_directory2()
    wait_for_compare(main_window, qtbot, timeout=30000)

    main_window.start_synchronization()
    sync_thread = main_window.sync_thread

    qtbot.waitUntil(lambda: sync_thread.isRunning(), timeout=5000)
    qtbot.waitUntil(lambda: len(active_children()) >= 1, timeout=10000)
    qtbot.waitUntil(lambda: len(list(dir2.glob("*.dat"))) >= 10, timeout=20000)

    assert sync_thread.isRunning()
    main_window.cancel_synchronization()

    wait_for_thread(qtbot, sync_thread, timeout=60000)
    qtbot.waitUntil(
        lambda: main_window.status_label.text() == C.STATUS_CANCELLED_ROLLED_BACK,
        timeout=60000,
    )
    qtbot.waitUntil(lambda: len(list(dir2.glob("*.dat"))) == 0, timeout=20000)
    qtbot.waitUntil(lambda: len(active_children()) == 0, timeout=20000)

    assert main_window.sync_btn.isEnabled()
    assert has_message(message_box_spy, "information", C.DIALOG_CANCELLED)


def test_report_dialog_updates_during_sync(qtbot, main_window, monkeypatch, tmp_path, message_box_spy):
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    create_files(dir1, 300, size=4096, prefix="report")
    dir2.mkdir()

    setup_directory_dialog(monkeypatch, [str(dir1), str(dir2)])

    main_window.select_directory1()
    main_window.select_directory2()
    wait_for_compare(main_window, qtbot, timeout=30000)

    main_window.start_synchronization()
    sync_thread = main_window.sync_thread

    main_window.show_report()
    qtbot.waitUntil(
        lambda: main_window.report_dialog is not None and main_window.report_dialog.isVisible(),
        timeout=5000,
    )
    qtbot.waitUntil(lambda: main_window.report_dialog.table.rowCount() > 0, timeout=30000)

    wait_for_thread(qtbot, sync_thread, timeout=40000)
    qtbot.waitUntil(lambda: main_window.report_dialog.progress_bar.value() >= 95, timeout=5000)

    main_window.report_dialog.close()


def test_apply_settings_filters_tree(qtbot, main_window, monkeypatch, tmp_path):
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    dir1.mkdir()
    dir2.mkdir()

    (dir1 / "keep.txt").write_text("keep", encoding="utf-8")
    (dir1 / "skip.txt").write_text("skip", encoding="utf-8")
    (dir1 / ".hidden.txt").write_text("hidden", encoding="utf-8")

    setup_directory_dialog(monkeypatch, [str(dir1), str(dir2)])
    monkeypatch.setattr(main_window.settings_manager, "save", lambda *_args, **_kwargs: None)

    main_window.select_directory1()
    main_window.select_directory2()
    wait_for_compare(main_window, qtbot, timeout=20000)

    settings = AppSettings(
        theme="dark",
        ignore_hidden=False,
        regex_rules=[RegexRule(action="exclude", pattern="skip")],
    )
    main_window.apply_settings(settings)
    wait_for_compare(main_window, qtbot, timeout=20000)

    tree_paths = collect_tree_paths(main_window.tree1)

    assert "keep.txt" in tree_paths
    assert "skip.txt" not in tree_paths
    assert ".hidden.txt" in tree_paths
    assert main_window.model.ignore_hidden is False


def test_main_window_trees_empty_on_startup(qtbot, main_window):
    """Both directory trees must be completely empty when the application starts."""
    assert main_window.tree1.base_path is None
    assert main_window.tree2.base_path is None
    assert main_window.tree1.model() is None
    assert main_window.tree2.model() is None
    assert main_window.dir1_path_display.text() == ""
    assert main_window.dir2_path_display.text() == ""


def test_trees_populate_after_directory_selection(qtbot, main_window, monkeypatch, tmp_path, message_box_spy):
    """Trees must show content only after the user selects directories."""
    dir1 = tmp_path / "source"
    dir2 = tmp_path / "target"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "a.txt").write_text("a", encoding="utf-8")
    (dir2 / "b.txt").write_text("b", encoding="utf-8")

    setup_directory_dialog(monkeypatch, [str(dir1), str(dir2)])

    main_window.select_directory1()
    main_window.select_directory2()
    wait_for_compare(main_window, qtbot, timeout=20000)

    assert main_window.tree1.base_path is not None
    assert main_window.tree2.base_path is not None
    assert main_window.tree1._proxy_model.rowCount(main_window.tree1.rootIndex()) > 0
    assert main_window.tree2._proxy_model.rowCount(main_window.tree2.rootIndex()) > 0
