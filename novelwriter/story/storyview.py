"""
novelWriter - GUI Story View
============================

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

import csv
import logging

from enum import Enum
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

from novelwriter import CONFIG, SHARED
from novelwriter.common import formatFileFilter
from novelwriter.constants import nwKeyWords, nwLabels, nwStats, trConst, trStats
from novelwriter.extensions.configlayout import NColorLabel
from novelwriter.extensions.modified import NIconButton, NPushButton
from novelwriter.extensions.novelselector import NovelSelector
from novelwriter.extensions.tabwidget import NTabWidget
from novelwriter.story.outline import GuiStoryOutlineView
from novelwriter.story.storysettings import OutlineViewSettings, StoryViewCollection, StoryViewSettings
from novelwriter.story.storyviewbase import GuiStoryViewBase

if TYPE_CHECKING:
    from collections.abc import Iterable

    from novelwriter.enum import nwChange

logger = logging.getLogger(__name__)


class GuiStoryView(QWidget):
    """GUI: Project Story View."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)

        self._views: StoryViewCollection | None = None

        icnSize = SHARED.theme.baseIconSize
        btnSize = 1.4 * icnSize

        # Story View
        self.titleLabel = NColorLabel(
            self.tr("Story View"),
            self,
            color=SHARED.theme.helpText,
            scale=NColorLabel.HEADER_SCALE,
            bold=True,
        )

        self.novelValue = NovelSelector(self)
        self.novelValue.setIncludeAll(True)
        self.novelValue.setMinimumWidth(200)
        self.novelValue.novelSelectionChanged.connect(self._novelValueChanged)

        self.exportData = NIconButton(self, btnSize, "export:action")
        self.exportData.setToolTip(self.tr("Export the story view data"))
        self.exportData.clicked.connect(self._exportData)

        # Mange Views
        self.manageLabel = NColorLabel(
            self.tr("Manage Views"),
            self,
            color=SHARED.theme.helpText,
            scale=NColorLabel.NORMAL_SCALE,
            bold=True,
        )

        # Tabs
        self.tabMain = NTabWidget(self)
        self.tabMain.setMovable(True)
        self.tabMain.currentChanged.connect(self._currentViewChanged)

        self.addView = NIconButton(self, btnSize, "add:add")
        self.addView.setToolTip(self.tr("Add a new view"))
        self.addView.clicked.connect(self._addNewView)

        self.delView = NIconButton(self, btnSize, "remove:remove")
        self.delView.setToolTip(self.tr("Delete current view"))
        self.delView.clicked.connect(self._deleteCurrentView)

        self.copyView = NIconButton(self, btnSize, "copy:action")
        self.copyView.setToolTip(self.tr("Duplicate current view"))
        self.copyView.clicked.connect(self._copyCurrentView)

        self.editView = NIconButton(self, btnSize, "edit:change")
        self.editView.setToolTip(self.tr("Edit current view"))
        self.editView.clicked.connect(self._editCurrentView)

        self.refreshView = NPushButton(self, self.tr("Refresh"), icnSize, "refresh:change")
        self.refreshView.setToolTip(self.tr("Refresh curent view"))
        self.refreshView.clicked.connect(self._refreshRequested)

        # Assemble
        self.topBox = QHBoxLayout()
        self.topBox.addWidget(self.titleLabel)
        self.topBox.addSpacing(8)
        self.topBox.addWidget(self.novelValue)
        self.topBox.addSpacing(8)
        self.topBox.addWidget(self.exportData)
        self.topBox.addSpacing(32)
        self.topBox.addWidget(self.manageLabel)
        self.topBox.addSpacing(8)
        self.topBox.addWidget(self.addView)
        self.topBox.addWidget(self.delView)
        self.topBox.addWidget(self.copyView)
        self.topBox.addWidget(self.editView)
        self.topBox.addSpacing(8)
        self.topBox.addWidget(self.refreshView)
        self.topBox.addStretch(1)
        self.topBox.setContentsMargins(4, 4, 0, 0)
        self.topBox.setSpacing(4)

        self.outerBox = QVBoxLayout()
        self.outerBox.addLayout(self.topBox)
        self.outerBox.addWidget(self.tabMain)
        self.outerBox.setContentsMargins(0, 0, 0, 0)
        self.outerBox.setSpacing(8)

        self.setLayout(self.outerBox)

    ##
    #  Methods
    ##

    def updateTheme(self) -> None:
        """Update theme elements."""
        self.titleLabel.setTextColors(color=SHARED.theme.helpText)
        self.novelValue.updateTheme()
        self.refreshView.refreshTheme()
        self.exportData.refreshTheme()
        self.tabMain.refreshTheme()
        for view in self._iterViews():
            view.updateTheme()

    def openProjectTasks(self) -> None:
        """Run open project tasks.

        The views are not loaded here, but lazily the first time the
        user switches to the story view, see viewStory.
        """
        self.novelValue.refreshNovelList()
        self.novelValue.setHandle(SHARED.project.data.getLastHandle("story"))

    def closeProjectTasks(self) -> None:
        """Run closing project tasks."""
        if self._views is not None:
            self._views.setStoryViewsOrder([v.settings.viewID for v in self._iterViews()])
        self._views = None
        while self.tabMain.count() > 0:
            self._removeTab(0)

    def viewStory(self) -> None:
        """Load the views if needed, and refresh the current view."""
        if self._views is None:
            self._loadViews()
        self._refreshCurrentView()

    ##
    #  Public Slots
    ##

    @pyqtSlot(str, Enum)
    def updateRootItem(self, tHandle: str, change: nwChange) -> None:
        """Refresh the novel selector when a root folder changes."""
        self.novelValue.refreshNovelList()

    ##
    #  Private Slots
    ##

    @pyqtSlot(str)
    def _novelValueChanged(self, tHandle: str) -> None:
        """Rebuild the current view for the newly selected novel folder."""
        SHARED.project.data.setLastHandle(tHandle or None, "story")
        self._refreshCurrentView()

    @pyqtSlot()
    def _refreshRequested(self) -> None:
        """Force a rebuild of the current view."""
        self._refreshCurrentView(force=True)

    @pyqtSlot(int)
    def _currentViewChanged(self, index: int) -> None:
        """Refresh the view that was switched to."""
        self._refreshCurrentView()

    @pyqtSlot()
    def _addNewView(self) -> None:
        """Add a new outline view."""
        view = OutlineViewSettings()
        view.setName(self.tr("Outline"))
        self._addView(view)

    @pyqtSlot()
    def _copyCurrentView(self) -> None:
        """Duplicate the current view."""
        if isinstance(current := self.tabMain.currentWidget(), GuiStoryViewBase):
            self._addView(StoryViewSettings.duplicate(current.settings))

    @pyqtSlot()
    def _deleteCurrentView(self) -> None:
        """Delete the current view."""
        if (
            self._views is not None
            and isinstance(current := self.tabMain.currentWidget(), GuiStoryViewBase)
            and SHARED.question(self.tr("Delete view '{0}'?").format(current.settings.name))
        ):
            self._views.removeStoryView(current.settings.viewID)
            self._removeTab(self.tabMain.currentIndex())

    @pyqtSlot()
    def _editCurrentView(self) -> None:
        """Open the settings dialog for the current view."""
        if isinstance(current := self.tabMain.currentWidget(), GuiStoryViewBase):
            current.openSettings()

    @pyqtSlot(str)
    def _viewSettingsChanged(self, viewID: str) -> None:
        """Save the changed view settings, and rebuild the view."""
        if self._views is not None:
            for view in self._iterViews():
                if view.settings.viewID == viewID:
                    self._views.setStoryView(view.settings)
                    self.tabMain.setTabText(self.tabMain.indexOf(view), view.settings.name)
                    view.refresh(self.novelValue.handle, force=True)
                    break

    @pyqtSlot()
    def _exportData(self) -> None:
        """Export the story outline data as a CSV file."""
        name = CONFIG.lastPath("outline") / f"{SHARED.project.data.fileSafeName}.csv"
        if path := QFileDialog.getSaveFileName(
            self, self.tr("Save Outline As"), str(name), formatFileFilter(["*.csv", "*"])
        )[0]:
            CONFIG.setLastPath("outline", path)
            logger.info("Writing CSV file: %s", path)
            with open(path, mode="w", newline="", encoding="utf-8") as csvFile:
                writer = csv.writer(csvFile, dialect="excel", quoting=csv.QUOTE_ALL)
                writer.writerows(self._dumpNovelData(self.novelValue.handle))

    ##
    #  Internal Functions
    ##

    def _loadViews(self) -> None:
        """Load the views collection and populate the tabs."""
        views = StoryViewCollection(SHARED.project)
        if len(views) == 0:
            view = OutlineViewSettings()
            view.setName(self.tr("Outline"))
            views.setStoryView(view)
        self._views = views

        # The current view is refreshed by the caller, not on tab change
        self.tabMain.blockSignals(True)
        for view in views.storyViews():
            self._addTab(view)
        self.tabMain.blockSignals(False)

    def _addView(self, view: StoryViewSettings) -> None:
        """Add a new view to the collection, and switch to it."""
        if self._views is not None:
            view.setOrder(max((v.order for v in self._views.storyViews()), default=-1) + 1)
            self._views.setStoryView(view)
            if (index := self._addTab(view)) >= 0:  # pragma: no branch
                self.tabMain.setCurrentIndex(index)

    def _addTab(self, view: StoryViewSettings) -> int:
        """Add a tab for a view, and return its index."""
        if isinstance(view, OutlineViewSettings):
            widget = GuiStoryOutlineView(self, view)
            widget.settingsChanged.connect(self._viewSettingsChanged)
            return self.tabMain.addTab(widget, view.name)
        return -1

    def _removeTab(self, index: int) -> None:
        """Remove a tab and release its widget."""
        if widget := self.tabMain.widget(index):  # pragma: no branch
            self.tabMain.removeTab(index)
            widget.setParent(None)

    def _iterViews(self) -> Iterable[GuiStoryViewBase]:
        """Iterate over the view widgets in tab order."""
        for i in range(self.tabMain.count()):
            if isinstance(view := self.tabMain.widget(i), GuiStoryViewBase):  # pragma: no branch
                yield view

    def _refreshCurrentView(self, force: bool = False) -> None:
        """Refresh the current view, if loaded and visible."""
        if (
            self._views is not None
            and self.isVisible()
            and isinstance(current := self.tabMain.currentWidget(), GuiStoryViewBase)
        ):
            current.refresh(self.novelValue.handle, force=force)

    def _dumpNovelData(self, rootHandle: str | None) -> list[list[str | int]]:
        """Dump all novel data into a table."""
        project = SHARED.project
        index = project.index
        sLabel = project.localLookup("Story Structure")
        nLabel = project.localLookup("Note")
        sKeys = sorted(index.getStoryKeys())
        nKeys = sorted(index.getNoteKeys())
        sMatch = [f"story.{k}" for k in sKeys]
        nMatch = [f"note.{k}" for k in nKeys]
        sHeaders = [f"{sLabel} ({k})" for k in sKeys]
        nHeaders = [f"{nLabel} ({k})" for k in nKeys]

        data: list[list[str | int]] = [
            [
                "H",
                self.tr("Title"),
                self.tr("Document"),
                self.tr("Line"),
                self.tr("Status"),
                trStats(nwLabels.STATS_NAME[nwStats.CHARS]),
                trStats(nwLabels.STATS_NAME[nwStats.WORDS]),
                trStats(nwLabels.STATS_NAME[nwStats.PARAGRAPHS]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.POV_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.FOCUS_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.CHAR_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.PLOT_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.TIME_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.WORLD_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.OBJECT_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.ENTITY_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.CUSTOM_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.STORY_KEY]),
                trConst(nwLabels.KEY_NAME[nwKeyWords.MENTION_KEY]),
                self.tr("Synopsis"),
                *sHeaders,
                *nHeaders,
            ]
        ]

        for tHandle, _, hItem in index.iterNovelStructure(rHandle=rootHandle, activeOnly=True):
            if hItem.level != "H0" and (nwItem := project.tree[tHandle]):
                refs = hItem.getReferences()
                comments = dict(hItem.comments.items())
                story = [comments.get(k, "") for k in sMatch]
                notes = [comments.get(k, "") for k in nMatch]
                data.append([
                    hItem.level,
                    hItem.title,
                    nwItem.itemName,
                    hItem.line,
                    nwItem.getImportStatus()[0],
                    hItem.charCount,
                    hItem.wordCount,
                    hItem.paraCount,
                    ", ".join(refs[nwKeyWords.POV_KEY]),
                    ", ".join(refs[nwKeyWords.FOCUS_KEY]),
                    ", ".join(refs[nwKeyWords.CHAR_KEY]),
                    ", ".join(refs[nwKeyWords.PLOT_KEY]),
                    ", ".join(refs[nwKeyWords.TIME_KEY]),
                    ", ".join(refs[nwKeyWords.WORLD_KEY]),
                    ", ".join(refs[nwKeyWords.OBJECT_KEY]),
                    ", ".join(refs[nwKeyWords.ENTITY_KEY]),
                    ", ".join(refs[nwKeyWords.CUSTOM_KEY]),
                    ", ".join(refs[nwKeyWords.STORY_KEY]),
                    ", ".join(refs[nwKeyWords.MENTION_KEY]),
                    hItem.synopsis,
                    *story,
                    *notes,
                ])

        return data
