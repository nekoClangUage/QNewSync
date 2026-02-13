"""
Tests for LazyDirectoryTreeWidget and HighlightProxyModel.

Covers:
- compiled_rules filtering via HighlightProxyModel.filterAcceptsRow
- LazyDirectoryTreeWidget.load_directory with compiled_rules
- Highlight groups (set, clear, remove)
- Header APIs (set_header_label, set_header_alignment)
"""

from pathlib import Path

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor

from app_settings import CompiledRegexRule, RegexRule, compile_regex_rules
from ui.lazy_directory_tree import HighlightProxyModel, LazyDirectoryTreeWidget


def _make_rules(patterns: list[tuple]) -> list[CompiledRegexRule]:
    """Helper: build CompiledRegexRule list from (action, pattern) tuples."""
    rules = [RegexRule(action=a, pattern=p) for a, p in patterns]
    compiled, errors = compile_regex_rules(rules)
    assert not errors, f"Unexpected compile errors: {errors}"
    return compiled


def _wait_for_model(qtbot, widget, timeout=3000):
    """Wait for QFileSystemModel to finish loading the root directory."""
    model = widget._file_model
    if model.rootPath():
        qtbot.waitUntil(
            lambda: model.rowCount(model.index(model.rootPath())) >= 0,
            timeout=timeout,
        )


# ---------------------------------------------------------------------------
# HighlightProxyModel unit tests
# ---------------------------------------------------------------------------


class TestHighlightProxyModel:
    def test_set_compiled_rules_stores_rules(self, qtbot):
        proxy = HighlightProxyModel()
        assert proxy._compiled_rules == []

        rules = _make_rules([("exclude", r"\.log$")])
        proxy.set_compiled_rules(rules)
        assert len(proxy._compiled_rules) == 1
        assert proxy._compiled_rules[0].pattern == r"\.log$"

    def test_set_compiled_rules_none_clears(self, qtbot):
        proxy = HighlightProxyModel()
        rules = _make_rules([("exclude", r"\.tmp$")])
        proxy.set_compiled_rules(rules)
        assert len(proxy._compiled_rules) == 1

        proxy.set_compiled_rules(None)
        assert proxy._compiled_rules == []

    def test_set_compiled_rules_empty_list(self, qtbot):
        proxy = HighlightProxyModel()
        proxy.set_compiled_rules([])
        assert proxy._compiled_rules == []

    def test_highlight_group_lifecycle(self, qtbot):
        proxy = HighlightProxyModel()
        color = QColor(255, 0, 0)

        proxy.set_highlight_group("g1", {Path("a.txt")}, color)
        assert "g1" in proxy._highlight_groups
        assert "a.txt" in proxy._highlight_groups["g1"]

        proxy.remove_highlight_group("g1")
        assert "g1" not in proxy._highlight_groups

    def test_clear_highlights(self, qtbot):
        proxy = HighlightProxyModel()
        color = QColor(0, 255, 0)
        proxy.set_highlight_group("g1", {Path("a.txt")}, color)
        proxy.set_highlight_group("g2", {Path("b.txt")}, color)

        proxy.clear_highlights()
        assert len(proxy._highlight_groups) == 0
        assert len(proxy._highlight_colors) == 0

    def test_filter_accepts_row_no_rules(self, qtbot):
        """Without rules, filterAcceptsRow always returns True."""
        proxy = HighlightProxyModel()
        assert proxy.filterAcceptsRow(0, QModelIndex()) is True

    def test_filter_accepts_row_no_source_model(self, qtbot):
        """Without a proper source model, filterAcceptsRow returns True."""
        proxy = HighlightProxyModel()
        rules = _make_rules([("exclude", r"\.log$")])
        proxy.set_compiled_rules(rules)
        assert proxy.filterAcceptsRow(0, QModelIndex()) is True


# ---------------------------------------------------------------------------
# LazyDirectoryTreeWidget integration tests
# ---------------------------------------------------------------------------


class TestLazyDirectoryTreeWidget:
    def test_load_directory_basic(self, qtbot, tmp_path):
        """Widget loads a directory without errors."""
        (tmp_path / "file1.txt").write_text("hello", encoding="utf-8")
        (tmp_path / "file2.py").write_text("world", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        assert widget._base_path == tmp_path.resolve()

    def test_load_directory_nonexistent(self, qtbot, tmp_path):
        """Loading a nonexistent directory is a no-op."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path / "nonexistent")

        assert widget._base_path is None

    def test_load_directory_with_compiled_rules(self, qtbot, tmp_path):
        """compiled_rules are passed to the proxy model."""
        (tmp_path / "keep.py").write_text("code", encoding="utf-8")
        (tmp_path / "skip.log").write_text("log", encoding="utf-8")

        rules = _make_rules([("exclude", r"\.log$")])

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path, compiled_rules=rules)

        assert len(widget._proxy_model._compiled_rules) == 1
        assert widget._proxy_model._compiled_rules[0].pattern == r"\.log$"

    def test_load_directory_clears_old_rules(self, qtbot, tmp_path):
        """Reloading without rules clears previous rules."""
        (tmp_path / "file.txt").write_text("data", encoding="utf-8")
        rules = _make_rules([("exclude", r"\.log$")])

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        widget.load_directory(tmp_path, compiled_rules=rules)
        assert len(widget._proxy_model._compiled_rules) == 1

        widget.load_directory(tmp_path)
        assert widget._proxy_model._compiled_rules == []

    def test_load_directory_with_highlights(self, qtbot, tmp_path):
        """Highlight files are passed to the proxy model."""
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        highlight = {Path("a.txt")}
        color = QColor(255, 0, 0)
        widget.load_directory(tmp_path, highlight_files=highlight, highlight_color=color)

        assert "default" in widget._proxy_model._highlight_groups

    def test_set_highlight_group(self, qtbot, tmp_path):
        """set_highlight_group delegates to proxy model."""
        (tmp_path / "x.txt").write_text("x", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        widget.set_highlight_group("sync", {Path("x.txt")}, QColor(0, 255, 0))
        assert "sync" in widget._proxy_model._highlight_groups

    def test_clear_highlights(self, qtbot, tmp_path):
        """clear_highlights removes all groups."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        widget.set_highlight_group("g1", {Path("a.txt")}, QColor(255, 0, 0))
        widget.clear_highlights()
        assert len(widget._proxy_model._highlight_groups) == 0

    def test_remove_highlight_group(self, qtbot, tmp_path):
        """remove_highlight_group removes only the specified group."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        widget.set_highlight_group("g1", {Path("a.txt")}, QColor(255, 0, 0))
        widget.set_highlight_group("g2", {Path("b.txt")}, QColor(0, 255, 0))
        widget.remove_highlight_group("g1")

        assert "g1" not in widget._proxy_model._highlight_groups
        assert "g2" in widget._proxy_model._highlight_groups

    def test_set_ignore_hidden(self, qtbot, tmp_path):
        """set_ignore_hidden updates internal state and filters."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        assert widget._ignore_hidden is True
        widget.set_ignore_hidden(False)
        assert widget._ignore_hidden is False

    def test_set_header_label(self, qtbot):
        """set_header_label updates proxy header label."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.set_header_label("Test Header")

        header_data = widget._proxy_model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        assert header_data == "Test Header"

    def test_set_header_alignment(self, qtbot):
        """set_header_alignment updates the QHeaderView default alignment."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        widget.set_header_alignment(Qt.AlignmentFlag.AlignCenter)

        alignment = widget.header().defaultAlignment()
        assert alignment & Qt.AlignmentFlag.AlignHCenter
        assert alignment & Qt.AlignmentFlag.AlignVCenter

    def test_clear_resets_state(self, qtbot, tmp_path):
        """clear() resets base_path and highlights."""
        (tmp_path / "f.txt").write_text("f", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)
        widget.set_highlight_group("g", {Path("f.txt")}, QColor(255, 0, 0))

        widget.clear()
        assert widget._base_path is None
        assert len(widget._proxy_model._highlight_groups) == 0

    def test_base_path_property(self, qtbot, tmp_path):
        """base_path property returns the resolved path."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        assert widget.base_path is None
        widget.load_directory(tmp_path)
        assert widget.base_path == tmp_path.resolve()


class TestLegacyRetirement:
    def test_legacy_header_compat_api_removed(self, qtbot):
        """Legacy header compatibility methods are no longer exposed."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        assert not hasattr(widget, "setHeaderLabel")
        assert not hasattr(widget, "headerItem")

# ---------------------------------------------------------------------------
# Filtering integration tests (proxy + filesystem model)
# ---------------------------------------------------------------------------


class TestEmptyInitialState:
    def test_initial_state_shows_no_items(self, qtbot):
        """A freshly constructed widget must render zero rows (no filesystem root)."""
        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)

        assert widget.base_path is None
        assert widget.model() is None

    def test_clear_hides_all_content(self, qtbot, tmp_path):
        """After clear(), the tree must return to the empty startup state."""
        (tmp_path / "file.txt").write_text("data", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        _wait_for_model(qtbot, widget)
        assert widget.model() is not None

        widget.clear()

        assert widget.base_path is None
        assert widget.model() is None


class TestFilteringIntegration:
    def test_exclude_rule_filters_files(self, qtbot, tmp_path):
        """Exclude rule causes proxy to reject matching files."""
        (tmp_path / "keep.py").write_text("code", encoding="utf-8")
        (tmp_path / "skip.log").write_text("log data", encoding="utf-8")
        (tmp_path / "also_keep.txt").write_text("text", encoding="utf-8")

        rules = _make_rules([("exclude", r"\.log$")])

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path, compiled_rules=rules)

        # Wait for the filesystem model to populate
        model = widget._file_model
        root_index = model.index(str(tmp_path.resolve()))
        qtbot.waitUntil(lambda: model.rowCount(root_index) > 0, timeout=3000)

        # Check proxy model filtering
        proxy = widget._proxy_model
        proxy_root = proxy.mapFromSource(root_index)
        visible_names = set()
        for row in range(proxy.rowCount(proxy_root)):
            idx = proxy.index(row, 0, proxy_root)
            visible_names.add(proxy.data(idx, Qt.ItemDataRole.DisplayRole))

        assert "keep.py" in visible_names
        assert "also_keep.txt" in visible_names
        assert "skip.log" not in visible_names

    def test_include_rule_filters_files(self, qtbot, tmp_path):
        """Include rule causes proxy to accept only matching files."""
        (tmp_path / "wanted.py").write_text("code", encoding="utf-8")
        (tmp_path / "unwanted.txt").write_text("text", encoding="utf-8")

        rules = _make_rules([("include", r"\.py$")])

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path, compiled_rules=rules)

        model = widget._file_model
        root_index = model.index(str(tmp_path.resolve()))
        qtbot.waitUntil(lambda: model.rowCount(root_index) > 0, timeout=3000)

        proxy = widget._proxy_model
        proxy_root = proxy.mapFromSource(root_index)
        visible_names = set()
        for row in range(proxy.rowCount(proxy_root)):
            idx = proxy.index(row, 0, proxy_root)
            visible_names.add(proxy.data(idx, Qt.ItemDataRole.DisplayRole))

        assert "wanted.py" in visible_names
        assert "unwanted.txt" not in visible_names

    def test_directories_always_visible(self, qtbot, tmp_path):
        """Directories pass through filtering even with strict rules."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.py").write_text("code", encoding="utf-8")

        rules = _make_rules([("include", r"\.py$")])

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path, compiled_rules=rules)

        model = widget._file_model
        root_index = model.index(str(tmp_path.resolve()))
        qtbot.waitUntil(lambda: model.rowCount(root_index) > 0, timeout=3000)

        proxy = widget._proxy_model
        proxy_root = proxy.mapFromSource(root_index)
        visible_names = set()
        for row in range(proxy.rowCount(proxy_root)):
            idx = proxy.index(row, 0, proxy_root)
            visible_names.add(proxy.data(idx, Qt.ItemDataRole.DisplayRole))

        assert "subdir" in visible_names

    def test_no_rules_shows_everything(self, qtbot, tmp_path):
        """Without rules, all files are visible."""
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        (tmp_path / "b.log").write_text("b", encoding="utf-8")
        (tmp_path / "c.py").write_text("c", encoding="utf-8")

        widget = LazyDirectoryTreeWidget()
        qtbot.addWidget(widget)
        widget.load_directory(tmp_path)

        model = widget._file_model
        root_index = model.index(str(tmp_path.resolve()))
        qtbot.waitUntil(lambda: model.rowCount(root_index) > 0, timeout=3000)

        proxy = widget._proxy_model
        proxy_root = proxy.mapFromSource(root_index)
        visible_names = set()
        for row in range(proxy.rowCount(proxy_root)):
            idx = proxy.index(row, 0, proxy_root)
            visible_names.add(proxy.data(idx, Qt.ItemDataRole.DisplayRole))

        assert "a.txt" in visible_names
        assert "b.log" in visible_names
        assert "c.py" in visible_names
