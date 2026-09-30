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

from PyQt6.QtCore import QModelIndex, QPoint, QPointF, Qt
from PyQt6.QtGui import QPainter, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QApplication, QStyleOptionViewItem

from novelwriter import CONFIG, SHARED
from novelwriter.constants import nwKeyWords
from novelwriter.enum import nwView
from novelwriter.models.outlinemodel import OutlineModel
from novelwriter.story.outline import GuiStoryOutlineView, _OutlineDelegate
from novelwriter.story.storysettings import OutlineViewSettings
from novelwriter.types import QtModCtrl, QtModNone, QtScrollAlwaysOff, QtScrollAsNeeded

ALL_SETTINGS = (
    "outline.syntaxColors",
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
    "outline.showSynopsis",
    "outline.showProgress",
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

    # Preferences are applied to the viewport
    CONFIG.hideVScroll = True
    view.initSettings()
    assert tree.verticalScrollBarPolicy() == QtScrollAlwaysOff
    CONFIG.hideVScroll = False
    view.initSettings()

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
    assert tree._delegate._tagCol == SHARED.theme.syntaxTheme.tag
    assert tree._delegate._keyCol == SHARED.theme.syntaxTheme.key
    assert tree._delegate._noteCol == SHARED.theme.syntaxTheme.note
    assert not any(tree.isColumnHidden(c) for c in range(7))
    assert model.node(model.index(11, 0)).progress == "Page 16 (81.9\u202f%)"  # type: ignore

    # Progress follows the page settings
    settings.setValue("outline.countPerPage", 100)
    settings.setValue("outline.clearDoublePage", False)
    view.refresh(None, force=True)
    assert model.node(model.index(11, 0)).progress == "Page 27 (81.9\u202f%)"  # type: ignore

    # Progress is relative to the project target if it is larger
    SHARED.project.data.setProjectTarget(6012, None, False)
    view.refresh(None, force=True)
    assert model.node(model.index(11, 0)).progress == "Page 27 (41.0\u202f%)"  # type: ignore
    settings.setValue("outline.useTargetCount", False)
    view.refresh(None, force=True)
    assert model.node(model.index(11, 0)).progress == "Page 27 (81.9\u202f%)"  # type: ignore

    # Everything disabled leaves chapters only
    for key in ALL_SETTINGS:
        settings.setValue(key, False)
    view.refresh(None, force=True)
    assert model.rowCount(root) == 3
    assert tree._delegate._worldKeys == []
    assert tree._delegate._tagCol == tree._delegate._textCol
    assert tree._delegate._keyCol == tree._delegate._textCol
    assert tree._delegate._noteCol == tree._delegate._textCol
    assert [tree.isColumnHidden(c) for c in range(7)] == [False, True, True, True, True, True, True]
    assert model.node(model.index(0, 0)).progress == ""  # type: ignore

    # No rebuild without a change
    model.clear()
    view.refresh(None)
    assert model.rowCount(root) == 0

    # Clearing resets the build state
    tree.clear()
    view.refresh(None)
    assert model.rowCount(root) == 3

    # Chapters can be hidden
    settings.setValue("outline.showChapters", False)
    settings.setValue("outline.showScenes", True)
    view.refresh(None, force=True)
    assert model.rowCount(root) == 5
    assert {model.node(model.index(r, 0)).level for r in range(5)} == {3}  # type: ignore


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
    header.resizeSection(OutlineModel.C_SYNOPSIS, 250)
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
    # Plot is now the last visible column, so it is stretched and not saved
    assert view.settings.getState("columns") == {
        "title": 300,
        "synopsis": 250,
        "characters": 160,
        "plot": 160,
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
    assert header.sectionSize(OutlineModel.C_SYNOPSIS) == 250

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

    # The stretched last column keeps its previous width
    settings = OutlineViewSettings()
    settings.setState("columns", {"synopsis": 300})
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    tree.saveColumnState()
    assert settings.getState("columns")["synopsis"] == 300


@pytest.mark.gui
def testStoryOutline_WheelScroll(qtbot, nwGUI, prjLipsum):
    """Test that the mouse wheel scrolls one item per step."""
    assert nwGUI.openProject(prjLipsum)

    settings = OutlineViewSettings()
    view = GuiStoryOutlineView(nwGUI, settings)
    view.resize(800, 200)
    view.show()
    view.refresh(None)

    tree = view.outlineContent
    vBar = tree.verticalScrollBar()
    assert vBar is not None
    qtbot.waitUntil(lambda: vBar.maximum() > 3)

    def scroll(steps: int, modifiers: Qt.KeyboardModifier = QtModNone) -> int:
        vBar.setValue(0)
        tree.wheelEvent(
            QWheelEvent(
                QPointF(10.0, 10.0),
                QPointF(10.0, 10.0),
                QPoint(0, 0),
                QPoint(0, -120 * steps),
                Qt.MouseButton.NoButton,
                modifiers,
                Qt.ScrollPhase.NoScrollPhase,
                False,
            )
        )
        return vBar.value()

    # One item per step, regardless of desktop setting
    lines = QApplication.wheelScrollLines()
    QApplication.setWheelScrollLines(3)
    assert scroll(1) == 1
    assert scroll(2) == 2
    QApplication.setWheelScrollLines(1)
    assert scroll(1) == 1

    # Control scrolls a page, as before
    QApplication.setWheelScrollLines(3)
    assert scroll(1, QtModCtrl) == vBar.pageStep()
    QApplication.setWheelScrollLines(lines)


@pytest.mark.gui
def testStoryOutline_Paint(qtbot, monkeypatch, nwGUI, prjLipsum):
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
        node._lists = (
            {
                nwKeyWords.POV_KEY: ["Jane"],
                nwKeyWords.FOCUS_KEY: ["John"],
                nwKeyWords.CHAR_KEY: ["Jane", "John", "Jack", "Jill", "James", "Julia", "Joseph", "Joanna"],
                nwKeyWords.PLOT_KEY: ["Main"],
                nwKeyWords.TIME_KEY: ["Morning", "Afternoon", "Evening", "Night"],
                nwKeyWords.WORLD_KEY: ["Europe"],
                nwKeyWords.ENTITY_KEY: ["Company"],
                nwKeyWords.CUSTOM_KEY: ["Custom"],
                nwKeyWords.MENTION_KEY: ["Jack"],
            }
            if i % 2
            else {nwKeyWords.FOCUS_KEY: ["John"]}
        )
        node._refs = {k: ", ".join(v) for k, v in node._lists.items()}
        if i % 2:
            node._progress = ""

    # Paint all rows with one selected
    tree.setCurrentIndex(model.index(3, 0))
    assert not view.grab().isNull()

    # Highlighted references in labelled, wrapped and plain cells
    tree.setHighlight({"jane", "jack", "main", "night", "company", "custom"})
    assert delegate._highlight == {"jane", "jack", "main", "night", "company", "custom"}
    assert not view.grab().isNull()

    # Highlights are cut at the elided length, and are not added past it
    node = model._nodes[1]
    formats = delegate._highlightFormats(node, nwKeyWords.CHAR_KEY, 0, 14)
    assert [(f.start, f.length) for f in formats] == [(0, 4), (12, 2)]
    formats = delegate._highlightFormats(node, nwKeyWords.CHAR_KEY, 6, 10)
    assert [(f.start, f.length) for f in formats] == [(6, 4)]

    # A single world option is wrapped
    delegate.setWorldKeys([nwKeyWords.WORLD_KEY])
    assert not view.grab().isNull()

    # Wrapped text is limited to whole lines within the height
    node = model._nodes[1]
    node._lists[nwKeyWords.PLOT_KEY] = [f"Plot{i}" for i in range(30)]
    node._refs[nwKeyWords.PLOT_KEY] = ", ".join(node._lists[nwKeyWords.PLOT_KEY])
    hLine = delegate._fm.height()
    pixmap = QPixmap(200, 200)
    painter = QPainter(pixmap)
    assert 2 * hLine - 2 <= delegate._paintWrapped(painter, 0, 0, 150, 2 * hLine + 5, node, nwKeyWords.PLOT_KEY)
    assert delegate._paintWrapped(painter, 0, 0, 150, 2 * hLine + 5, node, nwKeyWords.PLOT_KEY) <= 2 * hLine + 2
    assert delegate._paintWrapped(painter, 0, 0, 150, hLine, model._nodes[0], nwKeyWords.CHAR_KEY) == 0

    # Stacked values leave a line for each following key with references
    calls = []
    paintWrapped = _OutlineDelegate._paintWrapped

    def recordWrapped(self, painter, x, y, w, h, node, key, labelled=True):
        used = paintWrapped(self, painter, x, y, w, h, node, key, labelled)
        calls.append((key, y, h, used))
        return used

    node._lists[nwKeyWords.WORLD_KEY] = [f"World{i}" for i in range(30)]
    node._refs[nwKeyWords.WORLD_KEY] = ", ".join(node._lists[nwKeyWords.WORLD_KEY])
    keys = [nwKeyWords.WORLD_KEY, nwKeyWords.OBJECT_KEY, nwKeyWords.ENTITY_KEY]
    with monkeypatch.context() as mp:
        mp.setattr(_OutlineDelegate, "_paintWrapped", recordWrapped)
        delegate._paintStacked(painter, 0, 0, 150, 3 * hLine, node, keys)
        world, entity = calls
        assert world[:3] == (nwKeyWords.WORLD_KEY, 0, 2 * hLine)
        assert entity[:3] == (nwKeyWords.ENTITY_KEY, world[3], 3 * hLine - world[3])

        # A single key with references uses the full height
        calls.clear()
        delegate._paintStacked(painter, 0, 0, 150, 3 * hLine, node, [nwKeyWords.OBJECT_KEY, nwKeyWords.WORLD_KEY])
        assert calls[0][:3] == (nwKeyWords.WORLD_KEY, 0, 3 * hLine)

    painter.end()
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
