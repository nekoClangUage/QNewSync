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

from PyQt6.QtGui import QColor

# Window Settings
WINDOW_TITLE = "Directories Synchronizer"
MIN_WINDOW_WIDTH = 1280
MIN_WINDOW_HEIGHT = 720

# UI Labels
LABEL_DIRECTORY_1 = "Directory 1"
LABEL_DIRECTORY_2 = "Directory 2"
LABEL_READY = "Ready"
LABEL_COMPARING = "Comparing directories..."
LABEL_READY_TO_SYNC = "Ready to synchronize"
LABEL_SYNC_STARTED = "Synchronization started..."
LABEL_STARTING = "Starting..."

# Button Text
BTN_SYNCHRONIZE = "Synchronize"
BTN_STOP = "Stop"
BTN_CANCEL = "Cancel"

# Menu & Actions
MENU_DIRECTORIES = "Directories"
MENU_HELP = "Help"
ACTION_CHOOSE_DIR_1 = "Choose Directory 1"
ACTION_CHOOSE_DIR_2 = "Choose Directory 2"
ACTION_SETTINGS = "Settings"
ACTION_REPORT = "Report"
ACTION_SHOW_HELP = "Help"
MENU_ABOUT = "About"
ABOUT_DIALOG_TITLE = "About Compareror"

# Placeholders
PLACEHOLDER_SELECT_DIR = "Click here to select directory..."

# Dialog Titles
DIALOG_SELECT_DIR_1 = "Select directory 1"
DIALOG_SELECT_DIR_2 = "Select directory 2"
DIALOG_SETTINGS_WARNING = "Settings warning"
DIALOG_SETTINGS_ERROR = "Settings error"
DIALOG_ERROR = "Error"
DIALOG_DIR_SELECTION_ERROR = "Directory selection error"

# Messages
MSG_SELECT_BOTH_DIRS = "Select both directories"
MSG_FAILED_SAVE_SETTINGS = "Failed to save settings: {}"
MSG_SYNC_STOPPED = "Synchronization stopped"

# Object Names
OBJ_CENTRAL_WIDGET = "centralWidget"
OBJ_BOTTOM_ACTION_BTN = "bottomActionButton"

# Colors
COLOR_HIGHLIGHT_SYNC = QColor(0, 200, 0)
COLOR_HIGHLIGHT_ONLY_DIR2 = QColor(255, 100, 100)
COLOR_TRANSPARENT_BG = QColor(0, 0, 0, 0)  # Transparent

# Status Messages
STATUS_FINISHED = "Finished"
STATUS_STOPPING = "Stopping synchronization..."
STATUS_STOPPING_ROLLBACK = "Stopping synchronization before rollback..."
STATUS_SYNC_STOPPED = "Synchronization stopped"
STATUS_SYNC_STOPPED_ROLLBACK = "Synchronization stopped, rolling back changes..."
STATUS_SYNC_COMPLETED = "Synchronization completed"
STATUS_SYNC_COMPLETED_HIGHLIGHT = "Synchronization completed (highlight applied)"
STATUS_ROLLBACK_WITH_ERRORS = "Rollback completed with {} error(s)"
STATUS_CANCELLED_ROLLED_BACK = "Synchronization cancelled, changes rolled back"

# Dialog Titles
DIALOG_STOPPED = "Stopped"
DIALOG_SYNC_COMPLETED = "Synchronization completed"
DIALOG_ROLLBACK_ERRORS = "Rollback Errors"
DIALOG_CANCELLED = "Cancelled"
DIALOG_OPEN_FILE_ERROR = "Open file error"

# Message Body Templates
MSG_SYNC_STOPPED_USER = "Synchronization stopped by user"
MSG_SYNC_COMPLETED_TEMPLATE = (
    "Synchronization completed!\nCopied: {copied}\nReplaced: {replaced}\nSkipped: {skipped}\nUnchanged: {unchanged}"
)
MSG_SYNC_ERRORS_HEADER = "\n\nErrors:\n"
MSG_ROLLBACK_ERRORS_HEADER = "Rollback completed with errors:\n\n"
MSG_ROLLBACK_MORE_ERRORS = "\n\n... and {} more errors"
MSG_CANCELLED_SUCCESS = "Synchronization cancelled and all changes rolled back successfully"
MSG_OPEN_FILE_ERROR = "Failed to open file:\n{}\n\n{}"

# Error Fragments
ERR_FAILED_TO_DELETE = "Failed to delete "

# Units
UNITS_SPEED = ["B/s", "KB/s", "MB/s", "GB/s"]
UNIT_SPEED_TB = "TB/s"
