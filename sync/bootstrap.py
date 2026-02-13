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

"""Bootstrap helpers for sync package initialization."""

from __future__ import annotations

from threading import RLock

__all__ = ["ensure_strategies_registered"]

_registered = False
_lock = RLock()


def ensure_strategies_registered() -> None:
    """Ensure default strategy implementations are registered exactly once."""
    global _registered
    if _registered:
        return

    with _lock:
        if _registered:
            return

        # Import locally to avoid circular dependencies during module import.
        from sync.strategies import register_default_strategies

        register_default_strategies()
        _registered = True
