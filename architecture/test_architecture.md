# Test responsibility map

Inspected 2026-10-05. Arrows show the main source responsibility exercised by a test module, not measured coverage percentages.

```mermaid
flowchart LR
    Fixtures["conftest.py<br/>tmp_path, isolated_settings, model, backup, stop events"]
    subgraph CoreTests["Core and configuration tests"]
        InterfacesTest["test_interfaces.py"]
        ModelTest["test_directory_sync_model.py"]
        StrategyTest["test_strategies.py"]
        UtilsTest["test_utils.py"]
        SettingsTest["test_app_settings.py"]
    end
    subgraph FileTests["File execution and regression tests"]
        ExecutorTest["test_executor.py"]
        CopyTest["test_copying.py"]
        AtomicCopyTest["test_atomic_copy.py"]
        CancelTest["test_cancel_rollback.py"]
        EmptyTest["test_empty_dirs.py"]
        StopTest["test_stop_crash.py"]
    end
    subgraph UITests["Qt widgets and integration"]
        TreeTest["test_lazy_directory_tree.py"]
        ThemeTest["test_dracula_theme.py"]
        SettingsUITest["test_settings_dialog_ui.py"]
        AboutTest["test_about_dialog.py"]
        ConcurrencyTest["test_concurrency.py"]
        WindowTest["test_main_window_integration.py"]
        FlowTest["test_ui_integration.py"]
    end
    Interfaces["sync/interfaces.py"]
    Model["sync/directory_sync_model.py"]
    Strategies["sync/strategies.py"]
    Utils["sync/utils.py"]
    Config["app_settings.py"]
    Tree["ui/lazy_directory_tree.py"]
    Themes["ui/theme_manager.py / theme_provider.py"]
    SettingsUI["ui/settings_dialog.py"]
    About["ui/about_dialog.py"]
    Workers["ui/workers.py"]
    Window["ui/main_window.py / report_dialog.py"]

    Fixtures -. autouse settings isolation .-> UITests
    Fixtures -. temporary directories and core fixtures .-> CoreTests
    Fixtures -. temporary directories .-> FileTests
    InterfacesTest --> Interfaces
    ModelTest --> Model
    StrategyTest --> Strategies
    UtilsTest --> Utils
    SettingsTest --> Config
    ExecutorTest --> Strategies
    CopyTest --> Strategies
    AtomicCopyTest --> Strategies
    CancelTest --> Strategies
    EmptyTest --> Model
    StopTest --> Strategies
    TreeTest --> Tree
    ThemeTest --> Themes
    ThemeTest --> SettingsUI
    SettingsUITest --> SettingsUI
    AboutTest --> About
    ConcurrencyTest --> Workers
    ConcurrencyTest --> Model
    WindowTest --> Window
    WindowTest --> Workers
    FlowTest --> Workers
    FlowTest --> Model
```

Sources: [test fixtures](../tests/conftest.py), [pytest configuration](../pyproject.toml), [CI matrix](../.github/workflows/ci.yml). Settings isolation substitutes a temporary YAML path; filesystem tests work with temporary directories. Qt integration tests use pytest-qt.

Some concurrency tests primarily assert absence of crashes or result availability, rather than byte-level integrity and exact cancellation semantics. A test name is not evidence that all races are prevented.

[Atomic copy checks](../tests/test_atomic_copy.py) compare actual source, target and backup contents after success, injected write/backup/installation failures, stop and forced worker termination. Process-pool tests exercise named `partial` tasks under the default start method and `spawn`; operation-owned cleanup must preserve unrelated user files. These checks do not establish crash recovery for the whole application or correctness of overlapping model operations.
