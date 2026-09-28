"""
novelWriter - GUI Story View Tests
==================================

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

from pathlib import Path
from shutil import copyfile

import pytest

from PyQt6.QtWidgets import QFileDialog

from novelwriter import SHARED
from novelwriter.constants import nwFiles
from novelwriter.enum import nwChange, nwView
from novelwriter.shared import _GuiAlert
from novelwriter.story.outline import GuiStoryOutlineView
from novelwriter.story.storyviewsettings import StoryViewCollection, StoryViewSettings

from tests.helpers import cmpFiles


@pytest.mark.gui
def testStoryView_ExportData(monkeypatch, nwGUI, prjLipsum, fncPath, tstPaths):
    """Test exporting the story view outline data to a CSV file."""
    assert nwGUI.openProject(prjLipsum)
    nwGUI.rebuildIndex()
    nwGUI._changeView(nwView.STORY)

    storyView = nwGUI.storyView
    csvFile = fncPath / "outline.csv"

    # Cancelling the save dialog writes nothing
    with monkeypatch.context() as mp:
        mp.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
        storyView.exportData.click()
    assert not csvFile.exists()

    # Export the outline data to a CSV file
    with monkeypatch.context() as mp:
        mp.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(csvFile), ""))
        storyView.exportData.click()
    assert csvFile.exists()

    testFile = tstPaths.outDir / "guiStoryView_export.csv"
    compFile = tstPaths.refDir / "guiStoryView_export.csv"
    copyfile(csvFile, testFile)
    assert cmpFiles(testFile, compFile)


@pytest.mark.gui
def testStoryView_ManageViews(monkeypatch, nwGUI, prjLipsum):
    """Test adding, copying, moving and deleting story views."""
    assert nwGUI.openProject(prjLipsum)
    storyView = nwGUI.storyView
    tabMain = storyView.tabMain
    viewsFile = SHARED.project.storage.getMetaFile(nwFiles.VIEWS_FILE)
    assert isinstance(viewsFile, Path)
    viewsFile.unlink(missing_ok=True)

    def tabNames():
        return [tabMain.tabText(i) for i in range(tabMain.count())]

    def savedNames():
        return [v.name for v in StoryViewCollection(SHARED.project).storyViews()]

    # Views are not loaded until the story view is shown
    storyView.addView.click()
    assert tabMain.count() == 0
    assert not viewsFile.exists()

    # A default outline view is created on first show
    nwGUI._changeView(nwView.STORY)
    assert tabNames() == ["Outline"]
    assert savedNames() == ["Outline"]
    assert isinstance(tabMain.currentWidget(), GuiStoryOutlineView)

    # Only known view kinds get a tab
    assert storyView._addTab(StoryViewSettings()) == -1

    # Add and copy views
    storyView.addView.click()
    assert tabNames() == ["Outline", "Outline"]
    assert tabMain.currentIndex() == 1

    storyView.copyView.click()
    assert tabNames() == ["Outline", "Outline", "Outline 2"]
    assert tabMain.currentIndex() == 2
    assert savedNames() == ["Outline", "Outline", "Outline 2"]

    # Moving a view is not saved immediately
    tabBar = tabMain.tabBar()
    assert tabBar is not None
    tabBar.moveTab(2, 0)
    assert tabNames() == ["Outline 2", "Outline", "Outline"]
    assert savedNames() == ["Outline", "Outline", "Outline 2"]

    # Showing the view again does not reload the views
    nwGUI._changeView(nwView.STORY)
    assert tabMain.count() == 3

    # Refresh and theme update
    storyView.refreshView.click()
    storyView.updateTheme()
    storyView.updateRootItem("", nwChange.UPDATE)

    # Delete a view, but cancel
    with monkeypatch.context() as mp:
        mp.setattr(_GuiAlert, "finalState", False)
        storyView.delView.click()
    assert tabMain.count() == 3

    # Delete the current view
    tabMain.setCurrentIndex(0)
    storyView.delView.click()
    assert tabNames() == ["Outline", "Outline"]
    assert savedNames() == ["Outline", "Outline"]

    # The views and their order are restored on reopen
    tabBar.moveTab(1, 0)
    viewIDs = [tabMain.widget(i).settings.viewID for i in range(tabMain.count())]  # type: ignore
    assert nwGUI.closeProject(isYes=True)
    assert tabMain.count() == 0
    assert nwGUI.openProject(prjLipsum)
    nwGUI._changeView(nwView.STORY)
    assert [tabMain.widget(i).settings.viewID for i in range(tabMain.count())] == viewIDs  # type: ignore

    # All views can be deleted
    storyView.delView.click()
    storyView.delView.click()
    assert tabMain.count() == 0
    assert savedNames() == []

    # Copy and delete do nothing with no views
    storyView.copyView.click()
    storyView.delView.click()
    assert tabMain.count() == 0

    # A new view can be added to an empty list
    storyView.addView.click()
    assert tabNames() == ["Outline"]
    assert savedNames() == ["Outline"]


@pytest.mark.gui
def testStoryView_LastHandle(nwGUI, prjLipsum):
    """Test that the selected novel folder is restored on reopen."""
    assert nwGUI.openProject(prjLipsum)
    storyView = nwGUI.storyView
    novelValue = storyView.novelValue
    rootHandle = novelValue.firstHandle
    assert rootHandle is not None

    # Select the root folder, then the "All Novel Folders" entry
    novelValue.setCurrentIndex(novelValue.findData(rootHandle))
    assert SHARED.project.data.getLastHandle("story") == rootHandle
    novelValue.setCurrentIndex(novelValue.count() - 1)
    assert SHARED.project.data.getLastHandle("story") is None

    # Select the root folder, and reopen the project
    novelValue.setCurrentIndex(novelValue.findData(rootHandle))
    assert nwGUI.closeProject(isYes=True)
    assert nwGUI.openProject(prjLipsum)
    assert storyView.novelValue.handle == rootHandle
