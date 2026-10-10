# Component dependencies

Current implementation, inspected 2026-10-05. This diagram groups related classes to keep the dependency graph readable.

```mermaid
flowchart TB
    Entry["main.py"]
    subgraph UI["Presentation: ui/"]
        Window["MainWindow"]
        Trees["LazyDirectoryTreeWidget x2<br/>HighlightProxyModel / QFileSystemModel"]
        Dialogs["Settings / Help / About / Report dialogs"]
        Workers["Compare / Sync / Cancel QThread workers"]
        Theme["ThemeManager / AppThemeProvider"]
    end
    subgraph Core["Core: sync/"]
        Boot["ensure_strategies_registered"]
        Model["DirectorySyncModel"]
        Registry["Four global StrategyRegistry instances"]
        Contracts["Protocols and data models"]
        Utils["Progress / stop / batch utilities"]
    end
    subgraph Strategies["sync/strategies.py"]
        Scanner["DefaultDirectoryScanner"]
        Cache["CachingHashProvider"]
        Hash["DefaultHashProvider / hash workers"]
        Diff["FullHash / TwoPhase / Fast diff strategies"]
        Executor["DefaultSyncExecutor / copy workers"]
    end
    Config["app_settings.py<br/>SettingsManager / AppSettings / regex rules"]
    YAML[("settings.yaml")]
    FS[("Source / target / backup filesystem")]
    Processes["multiprocessing Pool / Manager"]
    Log["Optional sync_debug.log"]

    Entry --> Boot
    Entry --> Window
    Entry --> Theme
    Window --> Trees
    Window --> Dialogs
    Window --> Theme
    Window --> Config
    Window --> Model
    Window --> Workers
    Workers --> Model
    Model --> Boot
    Model --> Registry
    Model --> Contracts
    Model --> Config
    Boot --> Registry
    Registry -. stores instances .-> Scanner
    Registry -. stores instances .-> Cache
    Registry -. stores instances .-> Diff
    Registry -. stores instances .-> Executor
    Cache --> Hash
    Diff --> Cache
    Scanner --> FS
    Hash --> Processes
    Hash --> FS
    Executor --> Processes
    Executor --> FS
    Executor -. debug enabled .-> Log
    Config --> YAML
    Dialogs --> Config
```

Sources: [entry point](../main.py), [model](../sync/directory_sync_model.py), [registry/contracts](../sync/interfaces.py), [strategies](../sync/strategies.py), [UI](../ui/main_window.py), [configuration](../app_settings.py).

Registry locking protects registration/lookup, not concurrent operations on the stored executor. Utilities are shown as available core helpers; the graph does not imply that every strategy uses them. Retired UI modules are absent from the current tree.
