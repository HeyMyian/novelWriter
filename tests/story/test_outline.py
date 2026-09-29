"""
novelWriter - GUI Story Outline Tests
=====================================

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

import pytest

from PyQt6.QtCore import QModelIndex
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QStyleOptionViewItem

from novelwriter import CONFIG
from novelwriter.constants import nwKeyWords
from novelwriter.enum import nwView
from novelwriter.models.outlinemodel import OutlineModel
from novelwriter.story.outline import GuiStoryOutlineView
from novelwriter.story.storysettings import OutlineViewSettings
from novelwriter.types import QtScrollAlwaysOff, QtScrollAsNeeded

ALL_SETTINGS = (
    "outline.showParts",
    "outline.showScenes",
    "outline.showSections",
    "outline.showCharacters",
    "outline.showPlot",
    "outline.showWorld",
    "outline.showObject",
    "outline.showEntity",
    "outline.showCustom",
    "outline.showMentions",
)


@pytest.mark.gui
def testStoryOutline_Settings(qtbot, nwGUI, prjLipsum):
    """Test the outline view settings and build state."""
    assert nwGUI.openProject(prjLipsum)
    root = QModelIndex()

    # Scroll bars follow the config
    CONFIG.hideVScroll = True
    CONFIG.hideHScroll = True
    settings = OutlineViewSettings()
    view = GuiStoryOutlineView(nwGUI, settings)
    tree = view.outlineContent
    model = tree._model
    assert tree.verticalScrollBarPolicy() == QtScrollAlwaysOff
    assert tree.horizontalScrollBarPolicy() == QtScrollAlwaysOff

    CONFIG.hideVScroll = False
    CONFIG.hideHScroll = False
    tree.initViewport()
    assert tree.verticalScrollBarPolicy() == QtScrollAsNeeded
    assert tree.horizontalScrollBarPolicy() == QtScrollAsNeeded

    # Default settings
    view.refresh(None)
    assert model.rowCount(root) == 10
    assert tree._delegate._worldKeys == [nwKeyWords.WORLD_KEY]
    assert [tree.isColumnHidden(c) for c in range(7)] == [False, False, False, False, True, True, False]

    # Everything enabled
    for key in ALL_SETTINGS:
        settings.setValue(key, True)
    view.refresh(None, force=True)
    assert model.rowCount(root) == 12
    assert tree._delegate._worldKeys == [nwKeyWords.WORLD_KEY, nwKeyWords.OBJECT_KEY, nwKeyWords.ENTITY_KEY]
    assert not any(tree.isColumnHidden(c) for c in range(7))

    # Everything disabled leaves chapters only
    for key in ALL_SETTINGS:
        settings.setValue(key, False)
    view.refresh(None, force=True)
    assert model.rowCount(root) == 3
    assert tree._delegate._worldKeys == []
    assert [tree.isColumnHidden(c) for c in range(7)] == [False, True, True, True, True, True, False]

    # No rebuild without a change
    model.clear()
    view.refresh(None)
    assert model.rowCount(root) == 0

    # Clearing resets the build state
    tree.clear()
    view.refresh(None)
    assert model.rowCount(root) == 3


@pytest.mark.gui
def testStoryOutline_ColumnState(qtbot, nwGUI, prjLipsum):
    """Test saving and loading the column order and widths."""
    assert nwGUI.openProject(prjLipsum)
    nwGUI._changeView(nwView.STORY)
    storyView = nwGUI.storyView
    storyView.addView.click()

    view = storyView.tabMain.currentWidget()
    assert isinstance(view, GuiStoryOutlineView)
    tree = view.outlineContent
    header = tree.header()
    assert header is not None

    # Move and resize columns, and hide one
    header.moveSection(header.visualIndex(OutlineModel.C_SYNOPSIS), 1)
    header.resizeSection(OutlineModel.C_TITLE, 300)
    header.resizeSection(OutlineModel.C_PLOT, 200)
    header.resizeSection(OutlineModel.C_WORLD, 120)
    tree.setColumnHidden(OutlineModel.C_WORLD, True)

    # The state is saved when the project is closed
    assert nwGUI.closeProject(isYes=True)
    assert nwGUI.openProject(prjLipsum)
    nwGUI._changeView(nwView.STORY)

    view = storyView.tabMain.currentWidget()
    assert isinstance(view, GuiStoryOutlineView)
    tree = view.outlineContent
    header = tree.header()
    assert header is not None
    assert view.settings.getState("columns") == {
        "title": 300,
        "synopsis": header.sectionSize(OutlineModel.C_SYNOPSIS),
        "characters": 160,
        "plot": 200,
        "world": 160,
        "custom": 160,
        "mentions": 160,
    }
    assert [header.logicalIndex(i) for i in range(7)] == [
        OutlineModel.C_TITLE,
        OutlineModel.C_SYNOPSIS,
        OutlineModel.C_CHARS,
        OutlineModel.C_PLOT,
        OutlineModel.C_WORLD,
        OutlineModel.C_CUSTOM,
        OutlineModel.C_MENTION,
    ]
    assert header.sectionSize(OutlineModel.C_TITLE) == 300
    assert header.sectionSize(OutlineModel.C_PLOT) == 200

    # Title stays first, unknown keys and invalid widths are skipped, and
    # missing columns are kept after the known ones
    settings = OutlineViewSettings()
    settings.setState("columns", {"plot": "wide", "unknown": 100, "title": 30, "mentions": 90})
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    header = tree.header()
    assert header is not None
    assert [header.logicalIndex(i) for i in range(3)] == [
        OutlineModel.C_TITLE,
        OutlineModel.C_PLOT,
        OutlineModel.C_MENTION,
    ]
    assert header.sectionSize(OutlineModel.C_TITLE) == 260
    assert header.sectionSize(OutlineModel.C_PLOT) == 160
    assert header.sectionSize(OutlineModel.C_MENTION) == 90

    # A hidden column without a previous width gets the default width
    settings = OutlineViewSettings()
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    tree.setColumnHidden(OutlineModel.C_CUSTOM, True)
    tree.saveColumnState()
    assert settings.getState("columns")["custom"] == 160


@pytest.mark.gui
def testStoryOutline_Paint(qtbot, nwGUI, prjLipsum):
    """Test painting the outline rows."""
    assert nwGUI.openProject(prjLipsum)

    settings = OutlineViewSettings()
    for key in ALL_SETTINGS:
        settings.setValue(key, True)

    view = GuiStoryOutlineView(nwGUI, settings)
    view.resize(1600, 800)
    view.refresh(None)
    view.updateTheme()

    tree = view.outlineContent
    model = tree._model
    delegate = tree._delegate

    # Fill in all reference types, with some left empty
    for i, node in enumerate(model._nodes):
        node._refs = (
            {
                nwKeyWords.POV_KEY: "Jane",
                nwKeyWords.FOCUS_KEY: "John",
                nwKeyWords.CHAR_KEY: "Jane, John, Jack, Jill, James, Julia, Joseph, Joanna",
                nwKeyWords.PLOT_KEY: "Main",
                nwKeyWords.TIME_KEY: "Morning, Afternoon, Evening, Night",
                nwKeyWords.WORLD_KEY: "Europe",
                nwKeyWords.ENTITY_KEY: "Company",
                nwKeyWords.CUSTOM_KEY: "Custom",
                nwKeyWords.MENTION_KEY: "Jack",
            }
            if i % 2
            else {nwKeyWords.FOCUS_KEY: "John"}
        )

    # Paint all rows with one selected
    tree.setCurrentIndex(model.index(3, 0))
    assert not view.grab().isNull()

    # Partition rows are a single line
    option = QStyleOptionViewItem()
    part = model.index(0, 0)
    chapter = model.index(1, 0)
    assert model.node(part).level == 1  # type: ignore
    assert delegate.sizeHint(option, part).height() < delegate.sizeHint(option, chapter).height()

    # Indices from other models fall back to default painting
    pixmap = QPixmap(100, 100)
    painter = QPainter(pixmap)
    delegate.paint(painter, option, QModelIndex())
    painter.end()
