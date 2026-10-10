# Settings and filtering

Current implementation, inspected 2026-10-05. Data classes and persistence live in [app_settings.py](../app_settings.py); controls live in [SettingsDialog](../ui/settings_dialog.py).

```mermaid
classDiagram
    direction LR
    class AppSettings {
        +theme
        +ignore_hidden
        +copy_empty_dirs
        +diff_mode
        +regex_rules
    }
    class RegexRule {
        <<frozen dataclass>>
        +action
        +pattern
    }
    class CompiledRegexRule {
        <<frozen dataclass>>
        +action
        +pattern
        +regex
    }
    class SettingsManager {
        +settings_path
        +load() tuple
        +save(settings)
        +load_from_path(path) tuple
        +save_to_path(settings, path)
    }
    class SettingsDialog {
        -_collect_settings()
        -_update_validation()
        -_apply_settings()
        -_import_settings()
        -_export_settings()
    }
    class MainWindow {
        +load_settings()
        +apply_settings(settings)
    }
    class DirectorySyncModel {
        +set_filters(options)
        +set_diff_mode(mode)
    }
    AppSettings o-- RegexRule : rule list
    SettingsManager --> AppSettings : load and serialize
    SettingsDialog --> SettingsManager : import and export
    SettingsDialog --> AppSettings : collect and validate
    MainWindow --> SettingsManager : load and save
    MainWindow --> SettingsDialog : opens
    MainWindow --> DirectorySyncModel : apply options
    DirectorySyncModel --> CompiledRegexRule : source filtering
```

```mermaid
flowchart LR
    YAML[("settings.yaml")]
    Load["safe_load / settings_from_dict"]
    Settings["AppSettings"]
    Save["settings_to_dict / safe_dump"]
    Compile["compile_regex_rules"]
    Validate["validate_regex_pattern<br/>syntax, lookbehind, nested quantifiers"]
    Rules["CompiledRegexRule list"]
    Path["Relative path"]
    Filter["should_include_path<br/>exclude first, then include whitelist"]
    Core["Source snapshot filtering"]
    Tree["Source tree proxy filtering"]
    YAML --> Load --> Settings --> Save --> YAML
    Settings --> Compile
    Compile --> Validate
    Compile --> Rules
    Rules --> Filter
    Path --> Filter
    Filter --> Core
    Filter --> Tree
```

Model defaults: `dark`, hidden ignored, empty directory propagation disabled, `two-phase`. The checked-in [settings.yaml](../settings.yaml) selects `strict`. Valid themes are dark/light/dracula; diff keys are strict/two-phase/fast.

Exclude matches win; include rules form a whitelist when present. Source core filtering also considers directory paths; the UI proxy keeps directories visible. Regex checks reject selected constructs but do not prove every accepted pattern has bounded runtime. Tests: [settings](../tests/test_app_settings.py), [settings UI](../tests/test_settings_dialog_ui.py), [tree](../tests/test_lazy_directory_tree.py).
