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
from novelwriter.story.outline import GuiOutlineViewSettings, GuiStoryOutlineView
from novelwriter.story.storysettings import OutlineViewSettings, StoryViewCollection, StoryViewSettings
from novelwriter.story.storyviewbase import GuiStoryViewBase

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

    # Copy, edit and delete do nothing with no views
    storyView.copyView.click()
    storyView.editView.click()
    storyView.delView.click()
    assert tabMain.count() == 0

    # A new view can be added to an empty list
    storyView.addView.click()
    assert tabNames() == ["Outline"]
    assert savedNames() == ["Outline"]


@pytest.mark.gui
def testStoryView_SettingsDialog(monkeypatch, nwGUI, prjLipsum):
    """Test editing story views with the settings dialog."""
    assert nwGUI.openProject(prjLipsum)
    storyView = nwGUI.storyView
    tabMain = storyView.tabMain
    viewsFile = SHARED.project.storage.getMetaFile(nwFiles.VIEWS_FILE)
    assert isinstance(viewsFile, Path)
    viewsFile.unlink(missing_ok=True)
    nwGUI._changeView(nwView.STORY)

    def openDialog() -> GuiOutlineViewSettings:
        storyView.editView.click()
        viewID = tabMain.currentWidget().settings.viewID  # type: ignore
        dialog = next(d for d in storyView._iterSettingsDialogs() if d.viewID == viewID)
        assert isinstance(dialog, GuiOutlineViewSettings)
        return dialog

    def savedValues():
        return [(v.name, v.getBool("outline.showScenes")) for v in StoryViewCollection(SHARED.project).storyViews()]

    asked = 0
    answer = True
    rebuilt = 0

    def question(*args, **kwargs) -> bool:
        nonlocal asked
        asked += 1
        return answer

    def refresh(self, rootHandle, force=False) -> None:
        nonlocal rebuilt
        rebuilt += int(force)

    monkeypatch.setattr(SHARED, "question", question)
    monkeypatch.setattr(GuiStoryOutlineView, "refresh", refresh)

    # Opening the dialog again reuses the open one
    dialog = openDialog()
    assert openDialog() is dialog

    # Saving updates the view and its tab, and rebuilds it
    dialog.viewName.setText("Scenes")
    dialog.showScenes.setChecked(False)
    dialog.btnSave.click()
    assert SHARED.findTopLevelWidget(GuiOutlineViewSettings) is None
    assert tabMain.tabText(0) == "Scenes"
    assert savedValues() == [("Scenes", False)]
    assert rebuilt == 1

    # A rename is saved on close without asking, and without a rebuild
    dialog = openDialog()
    dialog.viewName.setText("  Only  Scenes ")
    dialog.close()
    assert tabMain.tabText(0) == "Only Scenes"
    assert savedValues() == [("Only Scenes", False)]
    assert asked == 0
    assert rebuilt == 1

    # An empty name resolves to the default name
    dialog = openDialog()
    dialog.viewName.setText(" ")
    dialog.btnSave.click()
    assert tabMain.tabText(0) == "Outline"
    assert savedValues() == [("Outline", False)]
    assert rebuilt == 1

    # Closing without changes emits nothing
    dialog = openDialog()
    dialog.close()
    assert asked == 0
    assert rebuilt == 1

    # The sidebar, title and theme are handled by the base class
    dialog = openDialog()
    assert dialog.sidebar.accessibleName() == dialog.windowTitle()
    button = dialog.sidebar._group.button(1)
    assert button is not None
    button.click()
    storyView.updateTheme()

    # The Close button asks to save changes, which can be declined
    answer = False
    dialog.showScenes.setChecked(True)
    dialog.btnClose.click()
    assert SHARED.findTopLevelWidget(GuiOutlineViewSettings) is None
    assert savedValues() == [("Outline", False)]
    assert asked == 1
    assert rebuilt == 1
    answer = True

    # Settings for unknown views are ignored
    storyView._viewSettingsChanged("unknown", True)
    assert rebuilt == 1

    # A view that is hidden when its settings change is rebuilt when shown
    dialog = openDialog()
    dialog.showSections.setChecked(True)
    nwGUI._changeView(nwView.PROJECT)
    dialog.btnSave.click()
    assert rebuilt == 1
    nwGUI._changeView(nwView.STORY)
    assert rebuilt == 2
    nwGUI._changeView(nwView.PROJECT)
    nwGUI._changeView(nwView.STORY)
    assert rebuilt == 2

    # Deleting a view discards only its own open dialog, without asking
    asked = 0
    other = openDialog()
    storyView.addView.click()
    dialog = openDialog()
    dialog.showScenes.setChecked(False)
    storyView.delView.click()
    assert asked == 1
    assert list(storyView._iterSettingsDialogs()) == [other]
    assert savedValues() == [("Outline", False)]

    # Closing the project closes the dialog, and saves the changes
    assert openDialog() is other
    other.showScenes.setChecked(True)
    assert nwGUI.closeProject(isYes=True)
    assert asked == 2
    assert SHARED.findTopLevelWidget(GuiOutlineViewSettings) is None

    # Settings changes are ignored with no project open
    count = rebuilt
    storyView._viewSettingsChanged("unknown", True)
    assert rebuilt == count

    assert nwGUI.openProject(prjLipsum)
    assert savedValues() == [("Outline", True)]


@pytest.mark.gui
def testStoryView_LastHandle(nwGUI, prjLipsum):
    """Test that the selected novel folder is restored on reopen."""
    assert nwGUI.openProject(prjLipsum)
    storyView = nwGUI.storyView
    novelValue = storyView.novelValue
    rootHandle = novelValue.firstHandle
    assert rootHandle is not None

    # An invalid list format is rejected
    listFormat = novelValue._listFormat
    novelValue.setListFormat("No placeholder here")
    assert novelValue._listFormat == listFormat

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


@pytest.mark.gui
def testStoryView_LazyLoad(nwGUI, prjLipsum):
    """Test that views are only built when shown."""
    assert nwGUI.openProject(prjLipsum)
    storyView = nwGUI.storyView
    tabMain = storyView.tabMain
    novelValue = storyView.novelValue
    rootHandle = novelValue.firstHandle
    assert rootHandle is not None

    def built():
        return [tabMain.widget(i).outlineContent._built for i in range(tabMain.count())]  # type: ignore

    # Create two extra views, and reopen with the first view active
    nwGUI._changeView(nwView.STORY)
    storyView.addView.click()
    storyView.addView.click()
    tabMain.setCurrentIndex(0)
    assert nwGUI.closeProject(isYes=True)
    assert nwGUI.openProject(prjLipsum)
    assert tabMain.count() == 0

    # Only the active view is built when the story view is first shown
    nwGUI._changeView(nwView.STORY)
    assert built() == [True, False, False]

    # Other views are built when switched to
    tabMain.setCurrentIndex(2)
    assert built() == [True, False, True]

    # Changing the novel while hidden does not rebuild the view
    current = tabMain.currentWidget().outlineContent  # type: ignore
    nwGUI._changeView(nwView.PROJECT)
    novelValue.setCurrentIndex(novelValue.findData(rootHandle))
    assert current._lastHandle is None

    # It is rebuilt when the story view is shown again
    nwGUI._changeView(nwView.STORY)
    assert current._lastHandle == rootHandle


@pytest.mark.gui
def testStoryView_BaseClass(qtbot, nwGUI):
    """Test the story view base class."""
    settings = OutlineViewSettings()
    view = GuiStoryViewBase(nwGUI, settings)
    qtbot.addWidget(view)
    assert view.settings is settings

    # The default implementations do nothing
    view.updateTheme()
    view.refresh(None)
    view.openSettings()
