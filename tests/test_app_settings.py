"""
Tests for app_settings module: load/save, validation, regex security, diff_mode.
"""

from pathlib import Path

from app_settings import (
    VALID_DIFF_MODES,
    AppSettings,
    CompiledRegexRule,
    RegexRule,
    SettingsManager,
    compile_regex_rules,
    settings_from_dict,
    settings_to_dict,
    should_include_path,
    validate_regex_pattern,
)

# =============================================================================
# settings_from_dict / settings_to_dict
# =============================================================================


class TestSettingsFromDict:
    def test_defaults(self):
        settings, errors = settings_from_dict({})
        assert settings.theme == "dark"
        assert settings.ignore_hidden is True
        assert settings.diff_mode == "two-phase"
        assert settings.regex_rules == []
        assert errors == []

    def test_valid_full(self):
        data = {
            "theme": "light",
            "ignore_hidden": False,
            "diff_mode": "strict",
            "regex_rules": [{"action": "exclude", "pattern": r"\.tmp$"}],
        }
        settings, errors = settings_from_dict(data)
        assert settings.theme == "light"
        assert settings.ignore_hidden is False
        assert settings.diff_mode == "strict"
        assert len(settings.regex_rules) == 1
        assert errors == []

    def test_dracula_theme(self):
        data = {
            "theme": "dracula",
            "ignore_hidden": True,
            "diff_mode": "two-phase",
            "regex_rules": [],
        }
        settings, errors = settings_from_dict(data)
        assert settings.theme == "dracula"
        assert settings.ignore_hidden is True
        assert settings.diff_mode == "two-phase"
        assert settings.regex_rules == []
        assert errors == []

    def test_unknown_theme_falls_back(self):
        settings, errors = settings_from_dict({"theme": "neon"})
        assert settings.theme == "dark"
        assert any("neon" in e for e in errors)

    def test_unknown_diff_mode_falls_back(self):
        settings, errors = settings_from_dict({"diff_mode": "turbo"})
        assert settings.diff_mode == "two-phase"
        assert any("turbo" in e for e in errors)

    def test_all_valid_diff_modes(self):
        for mode in VALID_DIFF_MODES:
            settings, errors = settings_from_dict({"diff_mode": mode})
            assert settings.diff_mode == mode
            assert errors == []

    def test_invalid_regex_rule_format(self):
        settings, errors = settings_from_dict({"regex_rules": ["not_a_dict"]})
        assert len(settings.regex_rules) == 0
        assert any("invalid format" in e.lower() for e in errors)

    def test_invalid_regex_rule_action(self):
        settings, errors = settings_from_dict({"regex_rules": [{"action": "delete", "pattern": ".*"}]})
        assert len(settings.regex_rules) == 0
        assert any("invalid action" in e.lower() for e in errors)

    def test_empty_regex_pattern(self):
        settings, errors = settings_from_dict({"regex_rules": [{"action": "include", "pattern": ""}]})
        assert len(settings.regex_rules) == 0
        assert any("empty pattern" in e.lower() for e in errors)

    def test_regex_rules_not_a_list(self):
        settings, errors = settings_from_dict({"regex_rules": "bad"})
        assert len(settings.regex_rules) == 0
        assert any("must be a list" in e for e in errors)


class TestSettingsToDict:
    def test_roundtrip(self):
        original = AppSettings(
            theme="light",
            ignore_hidden=False,
            diff_mode="fast",
            regex_rules=[RegexRule("exclude", r"\.log$")],
        )
        data = settings_to_dict(original)
        restored, errors = settings_from_dict(data)
        assert errors == []
        assert restored.theme == original.theme
        assert restored.ignore_hidden == original.ignore_hidden
        assert restored.diff_mode == original.diff_mode
        assert len(restored.regex_rules) == 1
        assert restored.regex_rules[0].pattern == r"\.log$"


# =============================================================================
# SettingsManager load/save
# =============================================================================


class TestSettingsManager:
    def test_load_nonexistent_returns_defaults(self, tmp_path):
        mgr = SettingsManager(tmp_path / "missing.yaml")
        settings, errors = mgr.load()
        assert settings == AppSettings()
        assert errors == []

    def test_save_and_load(self, tmp_path):
        path = tmp_path / "settings.yaml"
        mgr = SettingsManager(path)

        original = AppSettings(theme="light", ignore_hidden=False, diff_mode="strict")
        mgr.save(original)

        loaded, errors = mgr.load()
        assert errors == []
        assert loaded.theme == "light"
        assert loaded.ignore_hidden is False
        assert loaded.diff_mode == "strict"

    def test_load_corrupt_yaml(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("key: [unclosed bracket", encoding="utf-8")

        mgr = SettingsManager(path)
        settings, errors = mgr.load()
        assert settings == AppSettings()
        assert any("YAML" in e for e in errors)

    def test_import_export(self, tmp_path):
        mgr = SettingsManager(tmp_path / "main.yaml")
        original = AppSettings(
            theme="light",
            diff_mode="fast",
            regex_rules=[RegexRule("include", r"\.py$")],
        )

        export_path = tmp_path / "export.yaml"
        mgr.save_to_path(original, export_path)

        loaded, errors = mgr.load_from_path(export_path)
        assert errors == []
        assert loaded.theme == "light"
        assert loaded.diff_mode == "fast"
        assert len(loaded.regex_rules) == 1


# =============================================================================
# compile_regex_rules
# =============================================================================


class TestCompileRegexRules:
    def test_valid_rules(self):
        rules = [
            RegexRule("include", r"\.py$"),
            RegexRule("exclude", r"__pycache__"),
        ]
        compiled, errors = compile_regex_rules(rules)
        assert len(compiled) == 2
        assert errors == []

    def test_invalid_regex(self):
        rules = [RegexRule("include", r"[invalid")]
        compiled, errors = compile_regex_rules(rules)
        assert len(compiled) == 0
        assert len(errors) > 0

    def test_nested_quantifiers_rejected(self):
        rules = [RegexRule("include", r"(a+)+")]
        compiled, errors = compile_regex_rules(rules)
        assert len(compiled) == 0
        assert any("nested" in e.lower() for e in errors)

    def test_lookbehind_rejected(self):
        rules = [RegexRule("include", r"(?<=foo)bar")]
        compiled, errors = compile_regex_rules(rules)
        assert len(compiled) == 0
        assert any("lookbehind" in e.lower() for e in errors)


# =============================================================================
# validate_regex_pattern
# =============================================================================


class TestValidateRegexPattern:
    def test_empty_pattern(self):
        errors = validate_regex_pattern("   ")
        assert any("empty" in e.lower() for e in errors)

    def test_valid_pattern(self):
        errors = validate_regex_pattern(r"\.py$")
        assert errors == []

    def test_lookbehind(self):
        errors = validate_regex_pattern(r"(?<=x)y")
        assert any("lookbehind" in e.lower() for e in errors)

    def test_negative_lookbehind(self):
        errors = validate_regex_pattern(r"(?<!x)y")
        assert any("lookbehind" in e.lower() for e in errors)

    def test_nested_quantifiers(self):
        errors = validate_regex_pattern(r"(a+)+")
        assert any("nested" in e.lower() for e in errors)

    def test_safe_quantifiers(self):
        errors = validate_regex_pattern(r"a+b*c?")
        assert errors == []


# =============================================================================
# should_include_path
# =============================================================================


class TestShouldIncludePath:
    def test_no_rules(self):
        assert should_include_path(Path("anything.txt"), []) is True

    def test_exclude_match(self):
        rules = [CompiledRegexRule("exclude", r"\.log$", __import__("re").compile(r"\.log$"))]
        assert should_include_path(Path("debug.log"), rules) is False
        assert should_include_path(Path("main.py"), rules) is True

    def test_include_only(self):
        import re

        rules = [CompiledRegexRule("include", r"\.py$", re.compile(r"\.py$"))]
        assert should_include_path(Path("main.py"), rules) is True
        assert should_include_path(Path("data.csv"), rules) is False

    def test_exclude_takes_priority(self):
        import re

        rules = [
            CompiledRegexRule("include", r"\.py$", re.compile(r"\.py$")),
            CompiledRegexRule("exclude", r"test_", re.compile(r"test_")),
        ]
        assert should_include_path(Path("main.py"), rules) is True
        assert should_include_path(Path("test_main.py"), rules) is False
