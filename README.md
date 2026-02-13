# Compareror

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![CI](https://github.com/yourusername/compareror/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/compareror/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> A PyQt6 desktop application for visual directory comparison and safe one-way synchronization (Directory 1 -> Directory 2).

## Overview

Compareror is built around a layered architecture with a strategy-driven synchronization core:

- **Facade:** `DirectorySyncModel` coordinates scan -> diff -> sync -> rollback.
- **Strategy Pattern:** scanner, hash, diff, and executor implementations are pluggable.
- **StrategyRegistry:** global thread-safe registries resolve strategy implementations lazily.
- **Safe Execution:** synchronization creates backups before overwrite and supports rollback after cancel/error.

## Current Architecture Snapshot

Aligned with `architecture/*.puml` and `architecture/ROADMAP.md` (updated Feb 2026):

- [x] `ensure_strategies_registered()` bootstrap (once-only, thread-safe registration)
- [x] Diff modes: `strict`, `two-phase` (default), `fast`
- [x] `CachingHashProvider` decorator for hash reuse by `(path, size, mtime)`
- [x] `LazyDirectoryTreeWidget` + `HighlightProxyModel` as active UI tree system
- [x] Regex filtering with ReDoS protections (nested quantifier + lookbehind checks)
- [x] Real-time sync statistics in `ReportDialog` (throttled updates)
- [x] Optional empty-directory propagation (`copy_empty_dirs`)
- [x] Test suite snapshot: **17 test files / 189 tests**

## Architecture Layers

| Layer | Core modules | Responsibility |
| --- | --- | --- |
| Entry Point | `main.py` | App startup, strategy bootstrap, theme provider wiring |
| Presentation | `ui/main_window.py`, `ui/lazy_directory_tree.py`, dialogs, worker threads | User interactions, async orchestration, tree rendering |
| Domain | `sync/directory_sync_model.py`, `sync/interfaces.py`, `sync/bootstrap.py`, `sync/utils.py` | Core sync workflow, contracts, registry lookup, utility primitives |
| Strategy Implementations | `sync/strategies.py` | Default scanner/hash/diff/executor implementations |
| Configuration | `app_settings.py`, `settings.yaml` | Settings model, validation, YAML persistence, regex rule compilation |

## PlantUML Documentation

See `architecture/` for full diagrams:

- `component_diagram.puml` — system-level dependencies and flow
- `strategy_pattern.puml` — protocol + registry + concrete strategy relationships
- `sequence_sync.puml` — compare/sync/cancel/rollback runtime sequence
- `settings_diagram.puml` — settings model, validation, persistence
- `ui_class_diagram.puml` — UI classes, workers, theme system
- `test_architecture.puml` — test topology and source coverage mapping

## Feature Set

- [x] Visual side-by-side comparison with highlighted differences
- [x] Three diff strategies (`strict`, `two-phase`, `fast`)
- [x] Parallel hashing/copying (multiprocessing pool)
- [x] Hash caching via `CachingHashProvider`
- [x] Cancel + rollback safety model
- [x] Regex include/exclude rules with ReDoS-aware validation
- [x] Hidden-file filtering
- [x] Empty directory copy support (`copy_empty_dirs`)
- [x] Theme system (`dark`, `light`, `dracula`) via `ThemeManager`
- [x] Live sync statistics and status reporting
- [ ] Sync profiles (planned)
- [ ] Configurable executor swapping (process/thread) (planned)
- [ ] Headless/CLI mode (planned)

## Installation

### Prerequisites

- Python **3.10+** (project currently developed on 3.13.7)
- Windows / Linux / macOS

### Run from source

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

### Development dependencies

```bash
pip install -r requirements-dev.txt
```

## Usage

1. Select **Directory 1** (source) and **Directory 2** (target).
2. Click compare (auto-triggered after valid selection) to build diff highlights.
3. Start synchronization to copy/replace needed files.
4. Use **Stop** to halt processing, or **Cancel** to halt and rollback.

### `settings.yaml` example

```yaml
theme: dark
ignore_hidden: true
copy_empty_dirs: false
diff_mode: two-phase      # strict | two-phase | fast
regex_rules:
  - action: exclude
    pattern: '.*\.tmp$'
  - action: include
    pattern: '.*\.py$'
```

## Build Executables

`build.py` wraps PyInstaller and applies platform-aware output paths:

- output: `dist/<platform>/`
- build cache: `build/<platform>/`
- bundled data files: `settings.yaml`, `settings_export.yaml`, `icon_for_program.png`
- Windows icon handling:
  - auto-converts `icon_for_program.(png|jpg|jpeg)` to `.ico` when Pillow is available
  - falls back to existing `.ico` if present

```bash
pip install -r requirements.txt pyinstaller

# Optional (Windows icon auto-conversion support)
pip install Pillow

python build.py
```

## Development

### Tests

```bash
pytest tests/
pytest tests/ --cov=sync --cov=ui --cov=app_settings --cov-report=term
```

### Ruff (lint + format)

```bash
ruff check .
ruff format --check .
```

### CI

GitHub Actions:

1. `ci.yml`: Ruff lint/format + pytest matrix (Python 3.11/3.12/3.13 on Ubuntu + Windows)
2. `build.yml`: PyInstaller builds for Windows/Linux/macOS

## Project Structure

```text
compareror/
├── main.py
├── app_settings.py
├── build.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── settings.yaml
├── settings_export.yaml
├── sync/
│   ├── bootstrap.py
│   ├── directory_sync_model.py
│   ├── interfaces.py
│   ├── strategies.py
│   └── utils.py
├── ui/
│   ├── main_window.py
│   ├── lazy_directory_tree.py
│   ├── settings_dialog.py
│   ├── report_dialog.py
│   ├── help_dialog.py
│   ├── about_dialog.py
│   ├── workers.py
│   ├── theme_manager.py
│   ├── theme_provider.py
│   └── constants.py
├── architecture/
│   ├── ROADMAP.md
│   ├── component_diagram.puml
│   ├── strategy_pattern.puml
│   ├── sequence_sync.puml
│   ├── settings_diagram.puml
│   ├── ui_class_diagram.puml
│   └── test_architecture.puml
├── tests/
│   ├── conftest.py
│   └── test_*.py (17 files / 189 tests)
└── .github/workflows/
    ├── ci.yml
    └── build.yml
```

## Roadmap

For details, see [`architecture/ROADMAP.md`](architecture/ROADMAP.md).

### Mid-term (v1.5)

- [ ] SyncContext refactor (operation-scoped stop/progress/stats context)
- [ ] Executor swapping via config (process vs thread)
- [ ] Sync profiles
- [ ] Conflict resolution UI
- [ ] Headless/CLI mode

### Long-term (v2.0)

- [ ] Cloud backends (S3, SFTP, Google Drive)
- [ ] Real-time sync (filesystem watchers)
- [ ] Plugin system
- [ ] Persistent on-disk hash cache

## License

Licensed under **GNU Affero General Public License v3.0 or later**. See [LICENSE](LICENSE).

---

**Status:** Active development · v1.0.0
