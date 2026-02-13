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

from PyQt6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ui.theme_manager import ThemeManager


class HelpDialog(QDialog):
    """Help dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setMinimumSize(600, 400)
        self.theme_manager = ThemeManager.instance()
        self.theme_manager.register(self, role="dialog")
        self.setup_ui()

    def setup_ui(self) -> None:
        """Sets up the dialog UI."""
        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(r"""
        <h2>Compareror Help</h2>

        <h3>1. Quick Start</h3>
        <p><b>Directory 1 (Source)</b>: The reference directory.</p>
        <p><b>Directory 2 (Target)</b>: The directory to be updated to match Source.</p>
        <ul>
            <li><b>Compare</b>: Scans both directories and highlights differences.
                <ul>
                    <li><span style="color: green;">Green</span>: New or updated files (will be copied).</li>
                    <li><span style="color: red;">Red</span>: Files only in Target (will be ignored/kept).</li>
                    <li>Black: Identical files.</li>
                </ul>
            </li>
            <li><b>Synchronize</b>: Copies new files and updates changed files from Source to Target. Files existing only in Target are left untouched.</li>
            <li><b>Stop</b>: Pauses/Stops the operation immediately.</li>
            <li><b>Cancel</b>: Stops and <b>Rolls Back</b> changes (restores original files).</li>
        </ul>

        <h3>2. Filtering Rules (Regex)</h3>
        <p>You can control which files are synced using Regular Expressions in Settings.</p>

        <h4>Rule Logic & Priority</h4>
        <ol>
            <li><b>Exclusion (Highest Priority)</b>: Matches against <b>Exclude</b> rules first. If a file matches, it is skipped.</li>
            <li><b>Inclusion (Whitelist Mode)</b>:
                <ul>
                    <li>If you have <b>zero</b> Include rules: The app syncs <b>everything</b> (except Excluded files).</li>
                    <li>If you have <b>one or more</b> Include rules: The app syncs <b>ONLY</b> files matching these rules. Everything else is ignored.</li>
                </ul>
            </li>
        </ol>

        <h4>Regex Syntax Guide</h4>
        <p>Patterns match against the <b>relative path</b> (e.g., <code>folder/file.txt</code>). Use forward slashes <code>/</code>.</p>
        <ul>
            <li><code>.</code> : Any single character</li>
            <li><code>*</code> : Zero or more of previous</li>
            <li><code>^</code> : Start of path</li>
            <li><code>$</code> : End of path</li>
            <li><code>\</code> : Escape special char (e.g., <code>\.</code> is a dot)</li>
            <li><code>[abc]</code> : Any of a, b, c</li>
            <li><code>(jpg|png)</code> : Logical OR</li>
        </ul>

        <h4>Examples</h4>
        <table border="1" cellspacing="0" cellpadding="4" style="border-collapse: collapse;">
            <tr><th align="left">Goal</th><th align="left">Action</th><th align="left">Pattern</th></tr>
            <tr>
                <td>Ignore .log files</td>
                <td>Exclude</td>
                <td><code>\.log$</code></td>
            </tr>
            <tr>
                <td>Ignore 'temp' folder at root</td>
                <td>Exclude</td>
                <td><code>^temp/</code></td>
            </tr>
            <tr>
                <td>Ignore '__pycache__' anywhere</td>
                <td>Exclude</td>
                <td><code>__pycache__</code></td>
            </tr>
            <tr>
                <td><b>Only</b> sync JPG/PNG images</td>
                <td>Include</td>
                <td><code>\.(jpg|png)$</code></td>
            </tr>
        </table>
        <p><i>Note: Nested quantifiers like <code>(a+)+</code> are disabled for performance safety.</i></p>

        <h3>3. Comparison Modes</h3>
        <ul>
            <li><b>Strict</b>: Hashes <b>every</b> file. 100% accurate, slowest.</li>
            <li><b>Two-Phase (Default)</b>: Checks Size & Date first. If different, checks Hash. Balanced.</li>
            <li><b>Fast</b>: Checks Size & Date <b>only</b>. Fastest, but ignores content changes if timestamp is unchanged.</li>
        </ul>

        <h3>4. Safety Features</h3>
        <ul>
            <li><b>Backups</b>: Original files are backed up before replacement.</li>
            <li><b>Rollback</b>: Clicking 'Cancel' restores original files from backup.</li>
            <li><b>Copy Empty Directories</b>: Option to replicate empty folder structures (disabled by default).</li>
        </ul>
        """)

        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)
