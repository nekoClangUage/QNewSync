# Roadmap and Technical Details

> Detailed overview of implemented solutions, dependencies, and development plans.
> Last updated: February 13, 2026.

---

## 1. Project Status

**Compareror** is a stable directory synchronization utility built on a modern architecture using PyQt6. The application core uses the **Strategy** pattern with a **StrategyRegistry** for pluggable algorithms, ensuring flexibility and testability.

### Implemented Features
*   [x] **Two-way Scanning** (Source/Target) via `DefaultDirectoryScanner` using `os.scandir`.
*   [x] **Multiple Diff Modes** — Strict (full MD5 hash), Two-Phase (size/mtime then hash), Fast (size/mtime only).
*   [x] **Parallel Execution** (Multiprocessing Pool) for hashing and file copying.
*   [x] **Hash Caching** — `CachingHashProvider` decorator caches by `(path, size, mtime)`.
*   [x] **Safe Synchronization** with automatic backup of replaced files and Rollback support.
*   [x] **Regex Filtering** with ReDoS protection (nested quantifier and lookbehind detection).
*   [x] **Copy Empty Directories** — optional propagation of empty directory structures.
*   [x] **Lazy Directory Tree** — `LazyDirectoryTreeWidget` using `QFileSystemModel` + `HighlightProxyModel` for performant, on-demand loading with diff highlighting and regex filtering.
*   [x] **GUI** with Dark/Light/Dracula themes, animated transitions, and centralized `ThemeManager` singleton.
*   [x] **Real-time Sync Stats** — live `ReportDialog` with speed, progress, and per-file status (throttled ≤100ms).
*   [x] **Diff Mode Persistence** — `diff_mode` saved/loaded via `AppSettings` and `settings.yaml`.
*   [x] **Snapshot Cache Invalidation** — cached snapshots are cleared when directories or filters change.
*   [x] **Legacy UI Cleanup** — retired `DirectoryTreeWidget` / `AppStyle` code paths and moved `LazyDirectoryTreeWidget` to explicit header APIs (`set_header_label`, `set_header_alignment`).

---

## 2. Tech Stack and Dependencies

### Core Libraries
*   **Python 3.10+** (developed on 3.13.7)
*   **PyQt6 ≥6.6.0**: Main UI framework.
*   **PyYAML ≥6.0**: Configuration storage.

### Dev Dependencies
*   **ruff ≥0.9.0**: Linter / formatter.
*   **pytest ≥8.0.0**: Test framework.
*   **pytest-cov ≥6.0.0**: Coverage reporting.
*   **pytest-qt ≥4.4.0**: Qt widget testing.

### Internal Architecture
*   **`sync/interfaces.py`**: Protocols (`DirectoryScanner`, `HashProvider`, `DiffStrategy`, `SyncExecutor`), domain models (`FileMeta`, `DirectorySnapshot`, `DiffResult`, `SyncResult`), and `StrategyRegistry<T>`.
*   **`sync/strategies.py`**: Concrete strategy implementations (7 classes).
*   **`sync/directory_sync_model.py`**: Facade/coordinator — `DirectorySyncModel`.
*   **`sync/bootstrap.py`**: Thread-safe, once-only strategy registration.
*   **`sync/utils.py`**: `ThrottledProgressCallback`, `StopChecker`, `BatchProcessor`.
*   **`app_settings.py`**: `AppSettings`, `SettingsManager`, regex validation and compilation.
*   **`ui/main_window.py`**: `MainWindow` — main application window.
*   **`ui/lazy_directory_tree.py`**: `LazyDirectoryTreeWidget` + `HighlightProxyModel` (explicit header API).
*   **`ui/workers.py`**: `CompareWorkerThread`, `SyncWorkerThread`, `CancelWorkerThread`.
*   **`ui/theme_manager.py`**: `ThemeManager` singleton with animated transitions.
*   **`ui/theme_provider.py`**: `AppThemeProvider` — stylesheet/palette builder.
*   **`ui/settings_dialog.py`**: Settings UI with regex rule editor.
*   **`ui/report_dialog.py`**: Live synchronization report.
*   **`ui/directory_tree_widget.py` / `ui/styles.py`**: retired placeholder modules kept only as explicit deprecation markers.

---

## 3. Architectural Nuances

### 3.1. Strategy Pattern & Registry
All core algorithms are defined as `Protocol` interfaces and registered in global `StrategyRegistry` instances. The `DirectorySyncModel` lazily fetches strategies on first use. New strategies can be registered at runtime without modifying existing code.

### 3.2. ReDoS Protection (Regular Expression Denial of Service)
The application allows users to input regular expressions for file filtering. To avoid "freezes" on complex patterns, a validator is implemented:
*   Nested quantifiers are prohibited (e.g., `(a+)+`) — detected by a stack-based parser.
*   Lookbehind constructions are prohibited (`(?<=`, `(?<!`).
*   Uses `app_settings._detect_nested_quantifiers` and `validate_regex_pattern`.

### 3.3. Caching
*   **Hash Cache:** `CachingHashProvider` (Decorator pattern) remembers file hashes based on the key `(path, size, mtime)`. Speeds up repeated comparisons significantly.
*   **Snapshot Cache:** `DirectorySyncModel` caches `DirectorySnapshot` objects between comparisons. Invalidated when directories or filters change.
*   **WeakRef in Themes:** `ThemeManager` uses `WeakSet` for widget references, preventing memory leaks when dialog windows are closed.

### 3.4. Rollback Model
To guarantee data integrity during synchronization:
1.  **Backup First:** Before overwriting an existing file in Target, the original is copied to a temporary folder (`tempfile.mkdtemp`).
2.  **Stop Event:** If an operation is interrupted via `stop_event` or an error occurs, the Rollback procedure is triggered.
3.  **Restore:** Replaced files are restored from backup, copied files are deleted, and empty directories created during sync are removed.

### 3.5. Lazy Directory Tree
`LazyDirectoryTreeWidget` replaces the legacy `DirectoryTreeWidget` for the main UI:
*   Uses `QFileSystemModel` for on-demand, non-blocking directory loading.
*   `HighlightProxyModel` provides diff-result highlighting (foreground + background colors) and regex-based file filtering via `filterAcceptsRow`.
*   Directories are always visible (not filtered) to preserve tree structure.

---

## 4. Test Coverage

### Current Test Files (17 files, 189 tests)
*   `test_app_settings.py` — settings load/save, validation, regex security, `diff_mode`.
*   `test_directory_sync_model.py` — cache invalidation, nested-dir validation, `diff_mode`.
*   `test_interfaces.py` — protocol contracts, domain models, registry.
*   `test_strategies.py` — scanner, hash, diff, executor strategies.
*   `test_utils.py` — throttled callback, stop checker, batch processor.
*   `test_executor.py` — debug logging, stats throttling, copy errors, rollback.
*   `test_lazy_directory_tree.py` — proxy model, filtering, highlight groups, legacy-retirement assertions.
*   `test_empty_dirs.py` — empty directory copying and rollback.
*   `test_stop_crash.py` — race-condition regression (stop event inside worker result iteration).
*   `test_cancel_rollback.py`, `test_copying.py`, `test_concurrency.py` — sync integration tests.
*   `test_main_window_integration.py`, `test_ui_integration.py` — UI integration tests.
*   `test_dracula_theme.py` — Dracula theme validation, switching, persistence, caching.
*   `test_settings_dialog_ui.py` — diff mode radio buttons, persistence, import/export.
*   `test_about_dialog.py` — version parsing and About dialog UI/content behavior.

### Coverage Snapshot (measured)
Command used:

```bash
pytest tests/ --cov=sync --cov=ui --cov=app_settings --cov-report=term
```

Results:
*   **189 passed**
*   **Total coverage: 81%** (`2456` statements, `471` missed)

Key module coverage:
*   `sync/interfaces.py` — **97%**
*   `sync/utils.py` — **99%**
*   `app_settings.py` — **90%**
*   `sync/directory_sync_model.py` — **77%**
*   `sync/strategies.py` — **71%**
*   `ui/main_window.py` — **82%**
*   `ui/lazy_directory_tree.py` — **85%**
*   `ui/settings_dialog.py` — **68%**
*   `ui/workers.py` — **52%**
*   `ui/help_dialog.py` — **25%**
*   `ui/directory_tree_widget.py` — **100%** (retired placeholder module; retirement assertions)
*   `ui/styles.py` — **100%** (retired placeholder module; retirement assertions)

### Coverage Priorities
1.  Add focused tests for `ui/workers.py` thread lifecycle and callback cleanup branches.
2.  Add tests for `ui/help_dialog.py` rendering and content interactions.
3.  Add deeper branch coverage for `ui/settings_dialog.py` validation and import/export error handling.

---

## 5. Development Plan (Roadmap)

### Completed (v1.0 – v1.2)
- [x] **Strategy Architecture** — protocols, registry, bootstrap.
- [x] **Multiple Diff Modes** — strict, two-phase, fast.
- [x] **Hash Caching** — `CachingHashProvider` decorator.
- [x] **Lazy Directory Tree** — `QFileSystemModel` + `HighlightProxyModel`.
- [x] **Copy Empty Directories** — optional feature with rollback support.
- [x] **Real-time Stats** — `ReportDialog` with throttled updates.
- [x] **Diff Mode Persistence** — saved in `settings.yaml`.
- [x] **Snapshot Cache Invalidation** — on path/filter change.
- [x] **Debug Logging Control** — gated behind `debug_logging` flag.
- [x] **Stats Throttling** — `processed_items` capped at 500, callback ≤100ms.
- [x] **Legacy UI Class Retirement** — removed active `DirectoryTreeWidget`/`AppStyle` usage and removed lazy-tree compatibility shim.

### Mid-term Tasks (v1.5)
- [ ] **SyncContext Refactor** — decouple `stop_event`/callbacks into per-operation context objects.
- [x] **UI for Diff Mode** — diff mode selector added to `SettingsDialog` and covered by `test_settings_dialog_ui.py`.
- [ ] **Executor Swapping** — allow process vs thread executor via config.
- [ ] **Sync Profiles** — save/load settings presets (folder pairs, rules).
- [ ] **Conflict Resolution** — interface for choosing actions on version conflict.
- [ ] **Headless Mode** — CLI interface for task scheduler integration.

### Long-term Ideas (v2.0)
- [ ] **Cloud Support:** S3, SFTP, Google Drive.
- [ ] **Real-time Sync:** File system change tracking (Watchdog).
- [ ] **Plugins:** Plugin system for third-party developers.
- [ ] **On-disk Hash Cache:** Persistent hash cache between sessions.

---

## 6. Class & Pattern Futures

### 6.1. `DirectorySyncModel` Future Direction
`DirectorySyncModel` currently works as a stable facade/coordinator, but it still stores operation-scoped state (`stop_event`, progress/stats callbacks) on the instance. The planned **SyncContext** refactor should move transient operation state into explicit context objects passed through compare/sync/rollback flows.

Benefits:
*   cleaner concurrency model,
*   easier cancellation semantics,
*   simpler test setup for per-operation behavior.

### 6.2. Strategy Registry and Swappability
`StrategyRegistry<T>` + bootstrap already gives runtime pluggability and thread-safe registration. The next step is configuration-driven strategy selection (not only runtime default registration), especially for executor selection (process vs thread).

### 6.3. Pattern Maturity in Current Code
*   **Strategy Pattern:** mature and central to sync pipeline.
*   **Decorator Pattern:** `CachingHashProvider` is a well-isolated optimization layer.
*   **Facade Pattern:** `DirectorySyncModel` cleanly shields UI from low-level sync details.
*   **Singleton Pattern:** `ThemeManager` is stable and memory-safe via weak references.

### 6.4. Legacy Surface Reduction (Completed)
Legacy UI abstractions that no longer provide runtime value were removed from the active dependency graph:
*   `MainWindow` now uses explicit lazy-tree header APIs (`set_header_label`, `set_header_alignment`) instead of compatibility wrappers.
*   `ui/directory_tree_widget.py` and `ui/styles.py` are retained only as retired placeholders for clear migration guidance.

### 6.5. Practical Next Architectural Increments
*   Add typed operation context (`SyncContext`) for scan/diff/execute/rollback.
*   Add profile aggregate (`SyncProfile`) in settings domain to enable presets.
*   Keep protocols stable while adding optional advanced capabilities (conflict handlers, headless runner adapter).

---

## 7. Useful Commands

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=sync --cov=ui --cov=app_settings

# Generate diagrams (requires PlantUML)
java -jar plantuml.jar architecture/*.puml

# Run application
python main.py

# Lint
ruff check .
```
