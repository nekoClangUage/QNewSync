# UI classes and ownership

Current implementation, inspected 2026-10-05. Qt inheritance is explicit; associations show ownership and calls, not guaranteed exclusion between operations.

## Window, trees and dialogs

```mermaid
classDiagram
    direction LR
    class MainWindow {
        +tree1
        +tree2
        +compare_directories()
        +start_synchronization()
        +stop_synchronization()
        +cancel_synchronization()
    }
    class LazyDirectoryTreeWidget {
        +load_directory(path)
        +set_highlight_group(name, paths, color)
        +set_ignore_hidden(value)
        +set_header_label(label)
        +set_header_alignment(alignment)
        +clear()
    }
    class HighlightProxyModel {
        +set_compiled_rules(rules)
        +set_highlight_group(name, paths, color)
        +data(index, role)
        +filterAcceptsRow(row, parent)
    }
    class ReportDialog {
        +update_stats(stats)
        -_processed_count
    }
    QMainWindow <|-- MainWindow
    QTreeView <|-- LazyDirectoryTreeWidget
    QSortFilterProxyModel <|-- HighlightProxyModel
    QDialog <|-- SettingsDialog
    QDialog <|-- HelpDialog
    QDialog <|-- AboutDialog
    QDialog <|-- ReportDialog
    MainWindow *-- LazyDirectoryTreeWidget : source and target
    LazyDirectoryTreeWidget *-- QFileSystemModel
    LazyDirectoryTreeWidget *-- HighlightProxyModel
    MainWindow --> SettingsDialog : opens
    MainWindow --> HelpDialog : opens
    MainWindow --> AboutDialog : opens
    MainWindow --> ReportDialog : stats and report
```

`ClickableLineEdit` subclasses `QLineEdit` for path selection; `RoundedMenu` subclasses `QMenu` for menu presentation. They are created by MainWindow. Tree data loads through `QFileSystemModel`; regex/highlight behavior belongs to the proxy. Report cursor behavior with capped stats history is an open check, not a solved guarantee.

## Workers and the model

```mermaid
classDiagram
    direction LR
    class MainWindow {
        +model
        +cancel_requested
        +on_sync_finished(result)
        +on_cancel_finished(errors)
    }
    class CompareWorkerThread {
        +finished
        +progress
        +run()
    }
    class SyncWorkerThread {
        +finished
        +progress
        +stats_updated
        +run()
    }
    class CancelWorkerThread {
        +finished
        +progress
        +run()
    }
    MainWindow *-- DirectorySyncModel
    QThread <|-- CompareWorkerThread
    QThread <|-- SyncWorkerThread
    QThread <|-- CancelWorkerThread
    MainWindow --> CompareWorkerThread : start and signals
    MainWindow --> SyncWorkerThread : start and signals
    MainWindow --> CancelWorkerThread : start and signals
    CompareWorkerThread --> DirectorySyncModel : compare
    SyncWorkerThread --> DirectorySyncModel : sync
    CancelWorkerThread --> DirectorySyncModel : rollback
```

Workers share the window's model. Their custom result signals are emitted before thread exit. The full operation ordering is in [sequence_sync.md](sequence_sync.md).

## Themes

```mermaid
classDiagram
    direction LR
    class ThemeManager {
        +instance() ThemeManager
        +set_provider(provider)
        +register(widget)
        +apply_theme(theme)
        -_registered_widgets
        -_stylesheet_cache
        -_palette_cache
    }
    class ThemeProvider {
        <<Protocol>>
        +build_stylesheet(theme) str
        +build_palette(theme) QPalette
    }
    class AppThemeProvider
    QObject <|-- ThemeManager
    AppThemeProvider ..|> ThemeProvider
    ThemeManager --> ThemeProvider : delegates
    MainWindow --> ThemeManager : register and apply
    Dialogs --> ThemeManager : register
```

ThemeManager uses weak widget references, cached styles/palettes and animated transitions. Sources: [window](../ui/main_window.py), [workers](../ui/workers.py), [tree/proxy](../ui/lazy_directory_tree.py), [theme manager/provider](../ui/theme_manager.py), [provider implementation](../ui/theme_provider.py).
