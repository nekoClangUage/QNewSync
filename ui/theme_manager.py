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

import weakref
from typing import Protocol

from PyQt6.QtCore import QAbstractAnimation, QEasingCurve, QObject, QPropertyAnimation
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QWidget

from app_settings import VALID_THEMES


class ThemeProvider(Protocol):
    def build_stylesheet(self, theme: str) -> str: ...

    def build_palette(self, theme: str) -> QPalette: ...


class ThemeManager(QObject):
    _instance: ThemeManager | None = None

    def __init__(self) -> None:
        super().__init__()
        self._provider: ThemeProvider | None = None
        self._current_theme = "dark"
        self._stylesheet_cache: dict[str, str] = {}
        self._palette_cache: dict[str, QPalette] = {}
        self._registered_widgets: weakref.WeakSet[QWidget] = weakref.WeakSet()
        self._animations: weakref.WeakKeyDictionary[QWidget, QPropertyAnimation] = weakref.WeakKeyDictionary()
        self._transition_duration_ms = 180
        self._transition_delta = 0.18

    @classmethod
    def instance(cls) -> ThemeManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def set_provider(self, provider: ThemeProvider) -> None:
        if provider is self._provider:
            return
        self._provider = provider
        self._stylesheet_cache.clear()
        self._palette_cache.clear()

    def register(self, widget: QWidget, role: str = "default", animate: bool = False) -> None:
        if widget is None:
            return

        widget.setProperty("themeRole", role)
        self._registered_widgets.add(widget)
        self._apply_to_widget(widget, animate=animate)

    def apply_theme(self, theme: str, animate: bool = True) -> None:
        theme = self._normalize_theme(theme)
        self._current_theme = theme

        if not self._provider:
            return

        stylesheet = self._get_stylesheet(theme)
        palette = self._get_palette(theme)

        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)
            app.setPalette(palette)

        # Use a list to avoid issues with WeakSet changing during iteration
        for widget in list(self._registered_widgets):
            try:
                # Check if the underlying C++ object still exists
                if widget is not None and not self._is_deleted(widget):
                    self._apply_to_widget(widget, animate=animate)
                else:
                    self._registered_widgets.discard(widget)
            except (RuntimeError, AttributeError):
                self._registered_widgets.discard(widget)

    def set_transition_duration(self, duration_ms: int) -> None:
        self._transition_duration_ms = max(0, duration_ms)

    def _apply_to_widget(self, widget: QWidget, animate: bool) -> None:
        try:
            if widget is None or self._is_deleted(widget) or not self._provider:
                return

            palette = self._get_palette(self._current_theme)
            widget.setPalette(palette)

            # Re-polish to apply stylesheet changes
            style = widget.style()
            if style:
                style.unpolish(widget)
                style.polish(widget)

            widget.update()

            if animate:
                self._animate_widget(widget)
        except (RuntimeError, AttributeError):
            # Widget was likely deleted during the process
            if widget in self._registered_widgets:
                self._registered_widgets.discard(widget)

    def _is_deleted(self, widget: QWidget) -> bool:
        """Checks if a QWidget's underlying C++ object has been deleted."""
        try:
            # Accessing an attribute like objectName() will raise RuntimeError
            # if the C++ object has been deleted in PyQt6
            widget.objectName()
            return False
        except (RuntimeError, AttributeError):
            return True

    def _animate_widget(self, widget: QWidget) -> None:
        if not widget.isVisible() or not widget.isWindow():
            return

        existing = self._animations.get(widget)
        if existing and existing.state() == QAbstractAnimation.State.Running:
            existing.stop()

        animation = QPropertyAnimation(widget, b"windowOpacity", widget)
        animation.setDuration(self._transition_duration_ms)

        current_opacity = widget.windowOpacity() or 1.0
        start_opacity = min(current_opacity, 1.0) - self._transition_delta
        start_opacity = max(0.75, start_opacity)
        animation.setStartValue(start_opacity)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

        self._animations[widget] = animation

    def _get_stylesheet(self, theme: str) -> str:
        cached = self._stylesheet_cache.get(theme)
        if cached is None:
            cached = self._provider.build_stylesheet(theme) if self._provider else ""
            self._stylesheet_cache[theme] = cached
        return cached

    def _get_palette(self, theme: str) -> QPalette:
        cached = self._palette_cache.get(theme)
        if cached is None:
            cached = self._provider.build_palette(theme) if self._provider else QPalette()
            self._palette_cache[theme] = cached
        return QPalette(cached)

    @staticmethod
    def _normalize_theme(theme: str) -> str:
        normalized = (theme or "dark").lower()
        if normalized not in VALID_THEMES:
            return "dark"
        return normalized
