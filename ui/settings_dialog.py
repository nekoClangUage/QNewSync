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

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app_settings import VALID_THEMES, AppSettings, RegexRule, SettingsManager, validate_regex_pattern
from ui.theme_manager import ThemeManager


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, settings_manager: SettingsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.applied_settings: AppSettings | None = None
        self.validation_errors: list[str] = []

        self.setWindowTitle("Settings")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(860, 620)
        ThemeManager.instance().register(self, role="dialog")

        self.theme_radios: dict[str, QRadioButton] = {}
        self.diff_mode_radios: dict[str, QRadioButton] = {}

        self._build_ui()
        self._load_settings(settings)
        self._update_validation()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        general_group = QGroupBox("General")
        general_layout = QFormLayout()
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(0, 0, 0, 0)

        self.theme_group = QButtonGroup(self)
        for theme_name in VALID_THEMES:
            radio = QRadioButton(theme_name.capitalize())
            self.theme_radios[theme_name] = radio
            self.theme_group.addButton(radio)
            theme_layout.addWidget(radio)

        theme_layout.addStretch()

        diff_mode_widget = QWidget()
        diff_mode_layout = QHBoxLayout(diff_mode_widget)
        diff_mode_layout.setContentsMargins(0, 0, 0, 0)

        self.diff_mode_group = QButtonGroup(self)
        diff_mode_options = [
            ("strict", "Strict (Content Hash)"),
            ("two-phase", "Two-Phase (Size/Date + Hash)"),
            ("fast", "Fast (Size/Date)"),
        ]
        for mode_key, label in diff_mode_options:
            radio = QRadioButton(label)
            self.diff_mode_radios[mode_key] = radio
            self.diff_mode_group.addButton(radio)
            diff_mode_layout.addWidget(radio)

        diff_mode_layout.addStretch()

        self.ignore_hidden_checkbox = QCheckBox("Ignore hidden files/directories")
        self.copy_empty_dirs_checkbox = QCheckBox("Copy empty directories")

        general_layout.addRow("Theme:", theme_widget)
        general_layout.addRow("Diff Mode:", diff_mode_widget)
        general_layout.addRow("", self.ignore_hidden_checkbox)
        general_layout.addRow("", self.copy_empty_dirs_checkbox)
        general_group.setLayout(general_layout)
        main_layout.addWidget(general_group)

        rules_group = QGroupBox("Synchronization rules (Directory 1)")
        rules_layout = QVBoxLayout()

        self.rules_table = QTableWidget(0, 3)
        self.rules_table.setHorizontalHeaderLabels(["Action", "Pattern (regex)", "Status"])
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rules_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rules_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.rules_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        rules_layout.addWidget(self.rules_table)

        rules_buttons_layout = QHBoxLayout()
        self.add_rule_btn = QPushButton("Add Rule")
        self.remove_rule_btn = QPushButton("Remove Selected")
        self.add_rule_btn.clicked.connect(self._add_rule_row)
        self.remove_rule_btn.clicked.connect(self._remove_selected_rule)
        rules_buttons_layout.addWidget(self.add_rule_btn)
        rules_buttons_layout.addWidget(self.remove_rule_btn)
        rules_buttons_layout.addStretch()
        rules_layout.addLayout(rules_buttons_layout)


        self.errors_label = QLabel("")
        self.errors_label.setWordWrap(True)
        self.errors_label.setStyleSheet("color: #e46d6d;")
        rules_layout.addWidget(self.errors_label)

        self.warnings_label = QLabel("")
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setStyleSheet("color: #f0a34f;")
        rules_layout.addWidget(self.warnings_label)

        rules_group.setLayout(rules_layout)
        main_layout.addWidget(rules_group, stretch=1)

        bottom_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import...")
        self.export_btn = QPushButton("Export...")
        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")

        self.import_btn.clicked.connect(self._import_settings)
        self.export_btn.clicked.connect(self._export_settings)
        self.apply_btn.clicked.connect(self._apply_settings)
        self.cancel_btn.clicked.connect(self.reject)

        bottom_layout.addWidget(self.import_btn)
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.cancel_btn)
        bottom_layout.addWidget(self.apply_btn)
        main_layout.addLayout(bottom_layout)

    def _add_rule_row(self, rule: RegexRule | None = None) -> None:
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)

        action_combo = QComboBox()
        action_combo.addItems(["include", "exclude"])
        if rule and rule.action in {"include", "exclude"}:
            action_combo.setCurrentText(rule.action)

        pattern_edit = QLineEdit(rule.pattern if rule else "")
        status_label = QLabel("")
        status_label.setWordWrap(True)

        self.rules_table.setCellWidget(row, 0, action_combo)
        self.rules_table.setCellWidget(row, 1, pattern_edit)
        self.rules_table.setCellWidget(row, 2, status_label)

        action_combo.currentTextChanged.connect(self._update_validation)
        pattern_edit.textChanged.connect(self._update_validation)

        self._update_validation()

    def _remove_selected_rule(self) -> None:
        selected_rows = {index.row() for index in self.rules_table.selectedIndexes()}
        if not selected_rows:
            QMessageBox.information(self, "Remove rule", "Select a rule to remove.")
            return

        for row in sorted(selected_rows, reverse=True):
            self.rules_table.removeRow(row)

        self._update_validation()

    def _collect_rules(self) -> list[RegexRule]:
        rules: list[RegexRule] = []
        for row in range(self.rules_table.rowCount()):
            action_widget = self.rules_table.cellWidget(row, 0)
            pattern_widget = self.rules_table.cellWidget(row, 1)
            if not isinstance(action_widget, QComboBox) or not isinstance(pattern_widget, QLineEdit):
                continue
            rules.append(RegexRule(action=action_widget.currentText(), pattern=pattern_widget.text()))
        return rules

    def _collect_settings(self) -> AppSettings:
        theme = "dark"  # default
        for theme_name, radio in self.theme_radios.items():
            if radio.isChecked():
                theme = theme_name
                break

        diff_mode = "two-phase"  # default
        for mode_key, radio in self.diff_mode_radios.items():
            if radio.isChecked():
                diff_mode = mode_key
                break

        ignore_hidden = self.ignore_hidden_checkbox.isChecked()
        copy_empty_dirs = self.copy_empty_dirs_checkbox.isChecked()
        rules = self._collect_rules()
        return AppSettings(
            theme=theme,
            ignore_hidden=ignore_hidden,
            copy_empty_dirs=copy_empty_dirs,
            diff_mode=diff_mode,
            regex_rules=rules,
        )

    def _load_settings(self, settings: AppSettings) -> None:
        theme_to_set = settings.theme if settings.theme in self.theme_radios else "dark"
        if theme_to_set in self.theme_radios:
            self.theme_radios[theme_to_set].setChecked(True)

        diff_mode_to_set = settings.diff_mode if settings.diff_mode in self.diff_mode_radios else "two-phase"
        if diff_mode_to_set in self.diff_mode_radios:
            self.diff_mode_radios[diff_mode_to_set].setChecked(True)

        self.ignore_hidden_checkbox.setChecked(settings.ignore_hidden)
        self.copy_empty_dirs_checkbox.setChecked(settings.copy_empty_dirs)

        self.rules_table.setRowCount(0)
        for rule in settings.regex_rules:
            self._add_rule_row(rule)

        self._update_validation()

    def _update_validation(self) -> None:
        errors: list[str] = []
        warnings: list[str] = []
        include_patterns = set()
        exclude_patterns = set()

        for row in range(self.rules_table.rowCount()):
            action_widget = self.rules_table.cellWidget(row, 0)
            pattern_widget = self.rules_table.cellWidget(row, 1)
            status_label = self.rules_table.cellWidget(row, 2)

            if not isinstance(action_widget, QComboBox) or not isinstance(pattern_widget, QLineEdit):
                continue

            action = action_widget.currentText()
            pattern = pattern_widget.text()
            row_errors = validate_regex_pattern(pattern)

            if isinstance(status_label, QLabel):
                if row_errors:
                    status_label.setText("; ".join(row_errors))
                    status_label.setStyleSheet("color: #e46d6d;")
                else:
                    status_label.setText("OK")
                    status_label.setStyleSheet("color: #7bd97b;")

            if row_errors:
                errors.append(f"Rule #{row + 1}: {'; '.join(row_errors)}")
            else:
                if action == "include":
                    include_patterns.add(pattern)
                elif action == "exclude":
                    exclude_patterns.add(pattern)

        if include_patterns and exclude_patterns:
            warnings.append("Both include and exclude rules are active. Exclude rules take precedence.")

        conflicting = include_patterns.intersection(exclude_patterns)
        if conflicting:
            warnings.append("Conflicting patterns used for include and exclude: " + ", ".join(sorted(conflicting)))

        self.validation_errors = errors
        self.errors_label.setText("\n".join(errors))
        self.warnings_label.setText("\n".join(warnings))
        self.apply_btn.setEnabled(not errors)

    def _apply_settings(self) -> None:
        self._update_validation()
        if self.validation_errors:
            QMessageBox.warning(self, "Settings error", "Fix validation errors before applying.")
            return

        self.applied_settings = self._collect_settings()
        self.accept()

    def _import_settings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import settings",
            str(Path.cwd()),
            "YAML Files (*.yaml *.yml)",
        )
        if not file_path:
            return

        settings, errors = self.settings_manager.load_from_path(Path(file_path))
        if errors:
            QMessageBox.warning(self, "Import warning", "\n".join(errors))

        self._load_settings(settings)

    def _export_settings(self) -> None:
        self._update_validation()
        if self.validation_errors:
            QMessageBox.warning(self, "Export error", "Fix validation errors before exporting.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export settings",
            str(Path.cwd()),
            "YAML Files (*.yaml *.yml)",
        )
        if not file_path:
            return

        self.settings_manager.save_to_path(self._collect_settings(), Path(file_path))
        QMessageBox.information(self, "Export", "Settings exported successfully.")
