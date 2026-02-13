#!/usr/bin/env python3
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

"""
Utility script to count code lines in the project, excluding comments and blank lines.
"""

from pathlib import Path


def is_comment_line(line: str, in_multiline_comment: bool = False) -> tuple[bool, bool]:
    """
    Determines if a line is a comment.

    Args:
        line: The line of code to check.
        in_multiline_comment: Whether we are currently inside a multiline comment block.

    Returns:
        A tuple (is_comment, in_multiline_comment).
    """
    stripped = line.strip()

    # Blank lines are not counted as code
    if not stripped:
        return True, in_multiline_comment

    # Handle multiline comments
    if in_multiline_comment:
        if '"""' in stripped or "'''" in stripped:
            # Check if the comment closes on this line
            if stripped.count('"""') >= 1 or stripped.count("'''") >= 1:
                return True, False
            return True, True
        return True, True

    # Check for start of multiline comment
    if '"""' in stripped or "'''" in stripped:
        # Check if it opens and closes on the same line (e.g. one-line docstring)
        if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
            return True, False
        return True, True

    # Single line comments
    if stripped.startswith("#"):
        return True, False

    return False, in_multiline_comment


def count_code_lines(file_path: Path) -> int:
    """
    Counts lines of code (excluding comments) in a single file.

    Args:
        file_path: Path to the file.

    Returns:
        Number of code lines.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, encoding="cp1251") as f:
                lines = f.readlines()
        except Exception:
            return 0

    code_lines = 0
    in_multiline_comment = False

    for line in lines:
        is_comment, in_multiline_comment = is_comment_line(line, in_multiline_comment)
        if not is_comment:
            code_lines += 1

    return code_lines


def scan_project(root_dir: Path | str) -> tuple[int, dict[str, int]]:
    """
    Scans the project and counts code lines.

    Args:
        root_dir: Root directory of the project.

    Returns:
        A tuple (total_lines, file_stats_dict).
    """
    root_path = Path(root_dir)
    total_lines = 0
    file_stats = {}

    # Exclude virtual environments and git folders
    exclude_dirs = {".venv", "__pycache__", ".git", "venv", "env", "dist", "build"}

    for py_file in root_path.rglob("*.py"):
        # Skip files in excluded directories
        if any(exclude_dir in py_file.parts for exclude_dir in exclude_dirs):
            continue

        lines = count_code_lines(py_file)
        try:
            relative_path = py_file.relative_to(root_path)
            file_stats[str(relative_path)] = lines
            total_lines += lines
        except ValueError:
            continue

    return total_lines, file_stats


if __name__ == "__main__":
    project_dir = Path(__file__).parent
    total_lines, file_stats = scan_project(project_dir)

    print(f"Total lines of code (excluding comments): {total_lines}")
    print("\nBy file:")
    print("-" * 50)

    # Sort by line count (descending)
    sorted_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)

    for file_path, lines in sorted_files:
        print(f"{file_path}: {lines} lines")

    print("-" * 50)
    print(f"Total: {total_lines} lines of code")
