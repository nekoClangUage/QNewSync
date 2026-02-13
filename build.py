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

import argparse
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

APP_NAME = "Compareror"
ENTRY_POINT = "main.py"
DATA_FILES = ("settings.yaml", "settings_export.yaml", "icon_for_program.png")
ICON_PATHS = {
    "windows": "icon_for_program.ico",
    "linux": "icon_for_program.png",
    "darwin": "icon_for_program.icns",
}
BUILD_MODES = ("onedir", "onefile", "both")


@dataclass(frozen=True)
class BuildTarget:
    mode: str
    dist_dir: Path
    work_dir: Path
    mode_args: tuple[str, ...]


def generate_ico(source_path: Path, target_path: Path) -> None:
    """Convert an image to .ico format with multiple sizes."""
    if Image is None:
        print("WARNING: Pillow is not installed. Icon conversion skipped.")
        print("Install it with: pip install Pillow")
        return

    try:
        img = Image.open(source_path)
        # Sizes recommended for Windows icons
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        img.save(target_path, format="ICO", sizes=sizes)
        print(f"Generated icon: {target_path}")
    except Exception as exc:
        print(f"ERROR: Failed to convert icon: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Compareror with PyInstaller (onedir, onefile, or both)."
    )
    parser.add_argument(
        "--mode",
        choices=BUILD_MODES,
        default="both",
        help=(
            "Build mode: 'onedir' keeps the legacy folder layout with _internal, "
            "'onefile' creates a single executable, 'both' builds both outputs."
        ),
    )
    parser.add_argument(
        "--name",
        default=APP_NAME,
        help="Name of the generated executable (default: Compareror).",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Build console executable instead of GUI/windowed.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Disable PyInstaller --clean.",
    )
    return parser.parse_args()


def resolve_targets(root: Path, system: str, mode: str) -> list[BuildTarget]:
    selected_modes = [mode] if mode != "both" else ["onedir", "onefile"]
    targets: list[BuildTarget] = []

    for selected_mode in selected_modes:
        if selected_mode == "onedir":
            targets.append(
                BuildTarget(
                    mode="onedir",
                    dist_dir=root / "dist" / system,
                    work_dir=root / "build" / system / "onedir",
                    mode_args=("--onedir", "--contents-directory", "_internal"),
                )
            )
        else:
            targets.append(
                BuildTarget(
                    mode="onefile",
                    dist_dir=root / "dist" / system / "onefile",
                    work_dir=root / "build" / system / "onefile",
                    mode_args=("--onefile",),
                )
            )

    return targets


def build_icon_args(root: Path, system: str, icon_work_dir: Path) -> list[str]:
    icon_args: list[str] = []

    if system == "windows":
        source_icon = None
        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = root / f"icon_for_program{ext}"
            if candidate.exists():
                source_icon = candidate
                break

        if source_icon:
            icon_work_dir.mkdir(parents=True, exist_ok=True)
            target_ico = icon_work_dir / "icon_for_program.ico"
            print(f"Converting {source_icon.name} to .ico...")
            generate_ico(source_icon, target_ico)
            if target_ico.exists():
                icon_args = ["--icon", str(target_ico)]
        else:
            icon_path = root / "icon_for_program.ico"
            if icon_path.exists():
                icon_args = ["--icon", str(icon_path)]
    else:
        icon_name = ICON_PATHS.get(system)
        if icon_name:
            icon_path = root / icon_name
            if icon_path.exists():
                icon_args = ["--icon", str(icon_path)]

    return icon_args


def build_data_args(root: Path) -> list[str]:
    data_args: list[str] = []
    for data_file in DATA_FILES:
        data_path = root / data_file
        if data_path.exists():
            data_args.extend(["--add-data", f"{data_path}{os.pathsep}."])
        else:
            print(f"WARNING: Data file not found and will be skipped: {data_path}")

    return data_args


def expected_output_path(target: BuildTarget, executable_name: str, system: str) -> Path:
    if target.mode == "onefile":
        suffix = ".exe" if system == "windows" else ""
        return target.dist_dir / f"{executable_name}{suffix}"
    return target.dist_dir / executable_name


def run_pyinstaller(
    *,
    root: Path,
    target: BuildTarget,
    executable_name: str,
    windowed: bool,
    clean: bool,
    icon_args: list[str],
    data_args: list[str],
) -> int:
    target.dist_dir.mkdir(parents=True, exist_ok=True)
    target.work_dir.mkdir(parents=True, exist_ok=True)

    pyinstaller_args = ["--noconfirm", "--name", executable_name]

    if clean:
        pyinstaller_args.append("--clean")

    pyinstaller_args.append("--windowed" if windowed else "--console")
    pyinstaller_args.extend(target.mode_args)
    pyinstaller_args.extend(["--distpath", str(target.dist_dir)])
    pyinstaller_args.extend(["--workpath", str(target.work_dir)])
    pyinstaller_args.extend(["--specpath", str(target.work_dir)])
    pyinstaller_args.extend(icon_args)
    pyinstaller_args.extend(data_args)
    pyinstaller_args.append(ENTRY_POINT)

    print(f"Running PyInstaller for {target.mode} build...")
    completed = subprocess.run(
        [sys.executable, "-m", "PyInstaller", *pyinstaller_args],
        cwd=root,
        check=False,
    )
    return completed.returncode


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    system = platform.system().lower()
    clean = not args.no_clean
    windowed = not args.console

    targets = resolve_targets(root, system, args.mode)
    icon_args = build_icon_args(root, system, root / "build" / system / "assets")
    data_args = build_data_args(root)

    for target in targets:
        print(f"\n=== Build mode: {target.mode} ===")
        exit_code = run_pyinstaller(
            root=root,
            target=target,
            executable_name=args.name,
            windowed=windowed,
            clean=clean,
            icon_args=icon_args,
            data_args=data_args,
        )
        if exit_code != 0:
            print(f"ERROR: {target.mode} build failed with exit code {exit_code}.")
            return exit_code

        output_path = expected_output_path(target, args.name, system)
        print(f"SUCCESS: {target.mode} build output -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
