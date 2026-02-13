# Copyright (C) 2026 nekoClangUage
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern
from typing import Any

import yaml

DEFAULT_SETTINGS_FILENAME = "settings.yaml"
VALID_THEMES = ["dark", "light", "dracula"]
VALID_RULE_ACTIONS = {"include", "exclude"}
VALID_DIFF_MODES = {"strict", "two-phase", "fast"}


@dataclass(frozen=True)
class RegexRule:
    action: str
    pattern: str


@dataclass(frozen=True)
class CompiledRegexRule:
    action: str
    pattern: str
    regex: Pattern[str]


@dataclass
class AppSettings:
    theme: str = "dark"
    ignore_hidden: bool = True
    copy_empty_dirs: bool = False
    diff_mode: str = "two-phase"
    regex_rules: list[RegexRule] = field(default_factory=list)


class SettingsManager:
    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = settings_path or (Path(__file__).resolve().parent / DEFAULT_SETTINGS_FILENAME)

    def load(self) -> tuple[AppSettings, list[str]]:
        if not self.settings_path.exists():
            return AppSettings(), []

        return self.load_from_path(self.settings_path)

    def save(self, settings: AppSettings) -> None:
        self.save_to_path(settings, self.settings_path)

    def load_from_path(self, path: Path) -> tuple[AppSettings, list[str]]:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            return AppSettings(), [f"Failed to read settings: {exc}"]

        try:
            raw_data = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            return AppSettings(), [f"Failed to parse YAML: {exc}"]

        return settings_from_dict(raw_data)

    def save_to_path(self, settings: AppSettings, path: Path) -> None:
        data = settings_to_dict(settings)
        yaml_text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
        path.write_text(yaml_text, encoding="utf-8")


def settings_from_dict(data: dict[str, Any]) -> tuple[AppSettings, list[str]]:
    errors: list[str] = []

    theme = str(data.get("theme", "dark")).lower()
    if theme not in VALID_THEMES:
        errors.append(f"Unknown theme: {theme}")
        theme = "dark"

    ignore_hidden = bool(data.get("ignore_hidden", True))

    copy_empty_dirs = bool(data.get("copy_empty_dirs", False))

    diff_mode = str(data.get("diff_mode", "two-phase")).lower()
    if diff_mode not in VALID_DIFF_MODES:
        errors.append(f"Unknown diff mode: {diff_mode}")
        diff_mode = "two-phase"

    regex_rules_data = data.get("regex_rules", [])
    regex_rules: list[RegexRule] = []
    if isinstance(regex_rules_data, list):
        for idx, item in enumerate(regex_rules_data):
            if not isinstance(item, dict):
                errors.append(f"Regex rule #{idx + 1} has invalid format.")
                continue

            action = str(item.get("action", "")).lower()
            pattern = str(item.get("pattern", ""))
            if action not in VALID_RULE_ACTIONS:
                errors.append(f"Regex rule #{idx + 1} has invalid action '{action}'.")
                continue
            if not pattern:
                errors.append(f"Regex rule #{idx + 1} has empty pattern.")
                continue

            regex_rules.append(RegexRule(action=action, pattern=pattern))
    elif regex_rules_data:
        errors.append("regex_rules must be a list.")

    return AppSettings(
        theme=theme,
        ignore_hidden=ignore_hidden,
        copy_empty_dirs=copy_empty_dirs,
        diff_mode=diff_mode,
        regex_rules=regex_rules,
    ), errors


def settings_to_dict(settings: AppSettings) -> dict[str, Any]:
    return {
        "theme": settings.theme,
        "ignore_hidden": settings.ignore_hidden,
        "copy_empty_dirs": settings.copy_empty_dirs,
        "diff_mode": settings.diff_mode,
        "regex_rules": [{"action": rule.action, "pattern": rule.pattern} for rule in settings.regex_rules],
    }


def compile_regex_rules(rules: list[RegexRule]) -> tuple[list[CompiledRegexRule], list[str]]:
    compiled: list[CompiledRegexRule] = []
    errors: list[str] = []

    for idx, rule in enumerate(rules, start=1):
        validation_errors = validate_regex_pattern(rule.pattern)
        if validation_errors:
            errors.extend([f"Rule #{idx}: {msg}" for msg in validation_errors])
            continue

        try:
            regex = re.compile(rule.pattern)
        except re.error as exc:
            errors.append(f"Rule #{idx}: Regex error: {exc}")
            continue

        compiled.append(CompiledRegexRule(action=rule.action, pattern=rule.pattern, regex=regex))

    return compiled, errors


def should_include_path(path: Path, rules: list[CompiledRegexRule]) -> bool:
    if not rules:
        return True

    normalized_path = str(path).replace("\\", "/")
    include_rules = [rule for rule in rules if rule.action == "include"]
    exclude_rules = [rule for rule in rules if rule.action == "exclude"]

    for rule in exclude_rules:
        if rule.regex.search(normalized_path):
            return False

    if include_rules:
        return any(rule.regex.search(normalized_path) for rule in include_rules)

    return True


def validate_regex_pattern(pattern: str) -> list[str]:
    errors: list[str] = []
    if not pattern.strip():
        return ["Pattern is empty."]

    if "(?<=" in pattern or "(?<!" in pattern:
        errors.append("Lookbehind is not allowed.")

    nested_error = _detect_nested_quantifiers(pattern)
    if nested_error:
        errors.append(nested_error)

    try:
        re.compile(pattern)
    except re.error as exc:
        errors.append(f"Regex error: {exc}")

    return errors


def _detect_nested_quantifiers(pattern: str) -> str | None:
    stack: list[dict] = []
    escaped = False
    in_char_class = False
    length = len(pattern)

    idx = 0
    while idx < length:
        char = pattern[idx]

        if escaped:
            escaped = False
            idx += 1
            continue

        if char == "\\":
            escaped = True
            idx += 1
            continue

        if char == "[" and not in_char_class:
            in_char_class = True
            idx += 1
            continue

        if char == "]" and in_char_class:
            in_char_class = False
            idx += 1
            continue

        if in_char_class:
            idx += 1
            continue

        if char == "(":
            stack.append({"has_quantifier_inside": False})
            idx += 1
            continue

        if char == ")":
            if stack:
                group_info = stack.pop()
                quantifier_len = _quantifier_length(pattern, idx + 1)
                if quantifier_len and group_info["has_quantifier_inside"]:
                    return "Nested quantifiers are not allowed."
                if stack and (quantifier_len or group_info["has_quantifier_inside"]):
                    stack[-1]["has_quantifier_inside"] = True
            idx += 1
            continue

        if char in {"*", "+", "?"}:
            if stack:
                stack[-1]["has_quantifier_inside"] = True
            idx += 1
            continue

        if char == "{":
            quantifier_len = _quantifier_length(pattern, idx)
            if quantifier_len:
                if stack:
                    stack[-1]["has_quantifier_inside"] = True
                idx += quantifier_len
                continue

        idx += 1

    return None


def _quantifier_length(pattern: str, start: int) -> int:
    if start >= len(pattern):
        return 0

    char = pattern[start]
    if char in {"*", "+", "?"}:
        return 1

    if char != "{":
        return 0

    match = re.match(r"\{\d+(,\d*)?\}", pattern[start:])
    if not match:
        return 0
    return match.end()
