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
from PyQt6.QtGui import QDropEvent, QPainter, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QApplication, QStyleOptionViewItem

from novelwriter import CONFIG, SHARED
from novelwriter.constants import nwKeyWords
from novelwriter.enum import nwView
from novelwriter.models.outlinemodel import OutlineModel
from novelwriter.story.outline import GuiOutlineViewSettings, GuiStoryOutlineView, _OutlineDelegate
from novelwriter.story.storysettings import CommentColumn, OutlineViewSettings
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
    assert tree._delegate._modCol == SHARED.theme.syntaxTheme.mod
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

    # Row height follows the number of lines, within limits
    delegate = tree._delegate
    hLine = delegate._fm.height()
    assert delegate._rowHeight == delegate._lineHeight + 2 * hLine
    settings.setValue("outline.rowLines", 6)
    view.refresh(None, force=True)
    assert delegate._rowHeight == delegate._lineHeight + 5 * hLine
    delegate.setRowLines(1)
    assert delegate._rowHeight == delegate._lineHeight + 2 * hLine
    delegate.setRowLines(20)
    assert delegate._rowHeight == delegate._lineHeight + 9 * hLine

    # Everything disabled leaves chapters only
    for key in ALL_SETTINGS:
        settings.setValue(key, False)
    view.refresh(None, force=True)
    assert model.rowCount(root) == 3
    assert tree._delegate._worldKeys == []
    assert tree._delegate._tagCol == tree._delegate._textCol
    assert tree._delegate._keyCol == tree._delegate._textCol
    assert tree._delegate._noteCol == tree._delegate._textCol
    assert tree._delegate._modCol == tree._delegate._textCol
    assert [tree.isColumnHidden(c) for c in range(7)] == [False, True, True, True, True, True, False]
    assert model.node(model.index(0, 0)).progress == ""  # type: ignore

    # Comment columns without comments are hidden
    settings.setComments([*settings.comments, CommentColumn("empty", "Empty", ())])
    view.refresh(None, force=True)
    assert model.columnCount(root) == 8
    assert [tree.isColumnHidden(c) for c in (6, 7)] == [False, True]

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

    comments = f"comment:{view.settings.comments[0].cid}"  # type: ignore

    # Move and resize columns, and hide one
    header.moveSection(header.visualIndex(OutlineModel.C_COMMENTS), 1)
    header.resizeSection(OutlineModel.C_TITLE, 300)
    header.resizeSection(OutlineModel.C_COMMENTS, 250)
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
        comments: 250,
        "characters": 160,
        "plot": 160,
        "world": 160,
        "custom": 160,
        "mentions": 160,
    }
    assert [header.logicalIndex(i) for i in range(7)] == [
        OutlineModel.C_TITLE,
        OutlineModel.C_COMMENTS,
        OutlineModel.C_CHARS,
        OutlineModel.C_PLOT,
        OutlineModel.C_WORLD,
        OutlineModel.C_CUSTOM,
        OutlineModel.C_MENTION,
    ]
    assert header.sectionSize(OutlineModel.C_TITLE) == 300
    assert header.sectionSize(OutlineModel.C_COMMENTS) == 250

    # Changing the comment columns keeps the state by key, and adds new
    # columns at the end
    outline = view.settings
    assert isinstance(outline, OutlineViewSettings)
    header.resizeSection(OutlineModel.C_CHARS, 180)
    outline.setComments([CommentColumn("new", "New", ("note.new",)), *outline.comments])
    view.refresh(None, force=True)
    assert [header.logicalIndex(i) for i in range(3)] == [
        OutlineModel.C_TITLE,
        OutlineModel.C_COMMENTS + 1,
        OutlineModel.C_CHARS,
    ]
    assert header.logicalIndex(7) == OutlineModel.C_COMMENTS
    assert header.sectionSize(OutlineModel.C_COMMENTS + 1) == 250
    assert header.sectionSize(OutlineModel.C_CHARS) == 180
    assert header.sectionSize(OutlineModel.C_COMMENTS) == 160

    # Title stays first, unknown keys and invalid widths are skipped, and
    # missing columns are kept after the known ones
    settings = OutlineViewSettings()
    settings.setState("columns", {"plot": "wide", "unknown": 100, "title": 30, "mentions": 90})
    settings.setValue("outline.showMentions", True)
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    tree.refresh(None)
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

    # Nothing is saved before the state is loaded on the first build
    settings = OutlineViewSettings()
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    tree.saveColumnState()
    assert settings.getState("columns") is None

    # A hidden column without a previous width gets the default width
    tree.refresh(None)
    tree.setColumnHidden(OutlineModel.C_CUSTOM, True)
    tree.saveColumnState()
    assert settings.getState("columns")["custom"] == 160

    # The stretched last column keeps its previous width
    settings = OutlineViewSettings()
    comments = f"comment:{settings.comments[0].cid}"
    settings.setState("columns", {comments: 300})
    tree = GuiStoryOutlineView(nwGUI, settings).outlineContent
    tree.refresh(None)
    tree.saveColumnState()
    assert settings.getState("columns")[comments] == 300


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


@pytest.mark.gui
def testStoryOutline_CommentsPage(qtbot, nwGUI, prjLipsum):
    """Test the comment columns settings page."""
    assert nwGUI.openProject(prjLipsum)
    index = SHARED.project.index
    heading = index.getItemHeading("fb609cd8319dc", "T0001")
    assert heading is not None
    heading.setComment("story", "Goal", "Text")
    heading.setComment("note", "Consistency", "Text")
    heading.setComment("note", "consistency", "Text")
    for key in "ABC":
        heading.setComment("note", key, "Text")

    settings = OutlineViewSettings()
    settings.setComments([*settings.comments, CommentColumn("b", "Other", ("note.gone",))])
    dialog = GuiOutlineViewSettings(nwGUI, settings)
    qtbot.addWidget(dialog)
    page = dialog.commentsPage
    tree = page.columnTree
    combo = page.commentValue

    def options() -> list[str]:
        return [combo.itemData(i) for i in range(combo.count())]

    def keys(n: int) -> list[str]:
        section = tree.topLevelItem(n)
        assert section is not None
        return [section.child(i).data(0, page.D_KEY) for i in range(section.childCount())]  # type: ignore

    # The columns are loaded, and used keys are not in the options
    assert tree.topLevelItemCount() == 2
    assert keys(0) == ["synopsis"]
    assert keys(1) == ["note.gone"]
    assert tree.topLevelItem(1).child(0).text(0) == "Note: gone"  # type: ignore
    assert tree.topLevelItem(1).child(0).foreground(0).color() == SHARED.theme.helpText  # type: ignore
    assert options() == ["story.goal", "note.a", "note.b", "note.c", "note.consistency", "note.purpose"]
    assert combo.itemText(0) == "Story: Goal"
    assert combo.itemText(4) == "Note: Consistency"

    # Comments are added to the selected column, but only if the text matches
    tree.setCurrentItem(tree.topLevelItem(0))
    combo.setCurrentIndex(4)
    page.addComment.click()
    assert keys(0) == ["synopsis", "note.consistency"]
    assert "note.consistency" not in options()
    combo.setEditText("Nope")
    page.addComment.click()
    assert keys(0) == ["synopsis", "note.consistency"]

    # A column is full at five comments
    for _ in range(4):
        combo.setCurrentIndex(0)
        page.addComment.click()
    assert keys(0) == ["synopsis", "note.consistency", "story.goal", "note.a", "note.b"]
    assert options() == ["note.c", "note.purpose"]

    # Without a selection, comments are added to the last column
    tree.setCurrentItem(None)  # type: ignore
    page.addComment.click()
    assert keys(1) == ["note.gone", "note.c"]
    assert options() == ["note.purpose"]

    # Removing a comment only applies to comment items
    tree.setCurrentItem(tree.topLevelItem(1))
    page.delComment.click()
    assert keys(1) == ["note.gone", "note.c"]
    tree.setCurrentItem(tree.topLevelItem(1).child(1))  # type: ignore
    page.delComment.click()
    assert keys(1) == ["note.gone"]
    assert options() == ["note.c", "note.purpose"]

    # Columns are added, renamed and removed, with empty names replaced
    page.addColumn.click()
    assert tree.topLevelItemCount() == 3
    assert tree.currentItem() is tree.topLevelItem(2)
    page.editColumn.click()
    tree.topLevelItem(2).setText(0, "  ")  # type: ignore
    assert page.columns()[2].name == "Column"
    tree.setCurrentItem(tree.topLevelItem(0).child(1))  # type: ignore
    page.delColumn.click()
    assert tree.topLevelItemCount() == 2
    assert options() == ["synopsis", "story.goal", "note.a", "note.b", "note.c", "note.consistency", "note.purpose"]

    # Without a selection, the column controls do nothing
    tree.setCurrentItem(None)  # type: ignore
    page.editColumn.click()
    page.delColumn.click()
    assert tree.topLevelItemCount() == 2

    # Adding a comment without any columns creates one
    page.setColumns([])
    combo.setCurrentIndex(0)
    page.addComment.click()
    assert page.columns()[0].name == "Column"
    assert page.columns()[0].keys == ("synopsis",)

    # Drops are only accepted into columns with room
    page.setColumns([
        CommentColumn("a", "A", ("note.a",)),
        CommentColumn("b", "B", ("synopsis", "story.goal", "note.b", "note.c", "note.consistency")),
    ])
    source = tree.topLevelItem(0).child(0)  # type: ignore
    full = tree.topLevelItem(1)
    assert source is not None
    assert full is not None
    tree.setCurrentItem(source)

    def drop(target: QPoint) -> QDropEvent:
        event = QDropEvent(
            QPointF(target),
            Qt.DropAction.MoveAction,
            tree.mimeData([source]),
            Qt.MouseButton.LeftButton,
            QtModNone,
        )
        event.accept()
        tree.dropEvent(event)
        return event

    assert drop(tree.visualItemRect(full).center()).isAccepted() is False
    drop(tree.visualItemRect(tree.topLevelItem(0)).center())  # type: ignore
    drop(QPoint(-10, -10))
    assert [c.keys for c in page.columns()] == [
        ("note.a",),
        ("synopsis", "story.goal", "note.b", "note.c", "note.consistency"),
    ]

    # The page is saved to the settings
    dialog._applyChanges()
    assert [c.cid for c in settings.comments] != ["a", "b"]
    assert [c.cid for c in dialog._settings.comments] == ["a", "b"]  # type: ignore
    dialog.discardAndClose()
