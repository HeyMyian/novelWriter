"""
novelWriter - GUI Story View Base
=================================

This file is a part of novelWriter
Copyright (C) 2026 Veronica Berglyd Olsen and novelWriter contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""  # noqa

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from novelwriter.story.storysettings import StoryViewSettings


class GuiStoryViewBase(QWidget):
    """GUI: Story View Base Class.

    The base class for the views on the Story View tabs. Subclasses add
    their content to the outer layout and implement refresh.
    """

    def __init__(self, parent: QWidget, settings: StoryViewSettings) -> None:
        super().__init__(parent)

        self._settings = settings

        self.outerBox = QVBoxLayout()
        self.outerBox.setContentsMargins(0, 0, 0, 0)
        self.outerBox.setSpacing(0)

        self.setLayout(self.outerBox)

    ##
    #  Properties
    ##

    @property
    def settings(self) -> StoryViewSettings:
        """Return the view settings object."""
        return self._settings

    ##
    #  Methods
    ##

    def updateTheme(self) -> None:
        """Update theme elements."""
        return

    def refresh(self, rootHandle: str | None, force: bool = False) -> None:
        """Refresh the view content."""
        raise NotImplementedError
