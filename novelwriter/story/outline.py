"""
novelWriter - GUI Story Outline
===============================

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

import logging

from typing import TYPE_CHECKING

from PyQt6.QtCore import QModelIndex, QPointF, QRect, QSize, Qt
from PyQt6.QtGui import QFontMetrics, QPainter, QPalette, QTextCharFormat, QTextLayout, QTextOption
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from novelwriter import CONFIG, SHARED
from novelwriter.constants import nwKeyWords, nwLabels, nwUnicode, trConst
from novelwriter.extensions.modified import NTreeView
from novelwriter.extensions.switch import NSwitch
from novelwriter.models.outlinemodel import OutlineModel
from novelwriter.story.storyviewbase import GuiStorySettingsBase, GuiStoryViewBase
from novelwriter.types import (
    QtAlignLeftMiddle,
    QtAlignLeftTop,
    QtElideRight,
    QtHeaderInteractive,
    QtHeaderStretch,
    QtScrollAlwaysOff,
    QtScrollAsNeeded,
    QtTransparent,
)

if TYPE_CHECKING:
    from novelwriter.guimain import GuiMain
    from novelwriter.models.outlinemodel import OutlineNode
    from novelwriter.story.storysettings import OutlineViewSettings

logger = logging.getLogger(__name__)

LINE_FLAGS = int(Qt.TextFlag.TextSingleLine) | int(QtAlignLeftMiddle)
WRAP_FLAGS = int(Qt.TextFlag.TextWordWrap) | int(QtAlignLeftTop)

ROW_PAD = 3
ROW_RADIUS = 6

# Persistent column keys, independent of the column index
COLUMN_KEYS = {
    OutlineModel.C_TITLE: "title",
    OutlineModel.C_CHARS: "characters",
    OutlineModel.C_PLOT: "plot",
    OutlineModel.C_WORLD: "world",
    OutlineModel.C_CUSTOM: "custom",
    OutlineModel.C_MENTION: "mentions",
    OutlineModel.C_SYNOPSIS: "synopsis",
}


class GuiStoryOutlineView(GuiStoryViewBase):
    """GUI: Project Story Outline View."""

    def __init__(self, parent: QWidget, settings: OutlineViewSettings) -> None:
        super().__init__(parent, settings)

        self.outlineContent = GuiStoryOutlineTree(self, settings)
        self.outerBox.addWidget(self.outlineContent, 1)

    ##
    #  Methods
    ##

    def updateTheme(self) -> None:
        """Update theme elements."""
        self.outlineContent.updateTheme()

    def refresh(self, rootHandle: str | None, force: bool = False) -> None:
        """Refresh the outline content."""
        self.outlineContent.refresh(rootHandle, force=force)

    def saveViewState(self) -> None:
        """Save the view state to the settings object."""
        self.outlineContent.saveColumnState()

    def settingsDialog(self) -> type[GuiStorySettingsBase]:
        """Return the settings dialog class of the view."""
        return GuiOutlineViewSettings


class GuiOutlineViewSettings(GuiStorySettingsBase):
    """GUI: Outline View Settings Dialog."""

    def __init__(self, parent: GuiMain, settings: OutlineViewSettings) -> None:
        super().__init__(parent, settings)
        self.setTitle(self.tr("Outline View Settings"))

    def buildForm(self) -> None:
        """Build the form."""
        section = 0
        settings = self._settings

        iPx = SHARED.theme.baseIconHeight

        # Documents
        # =========

        title = settings.getLabel("outline.grpDocuments")
        section += 1
        self.sidebar.addButton(title, section)
        self.form.addGroupLabel(title, section)

        self.showParts = NSwitch(self, height=iPx)
        self.showScenes = NSwitch(self, height=iPx)
        self.showSections = NSwitch(self, height=iPx)

        self.form.addRow(settings.getLabel("outline.showParts"), self.showParts)
        self.form.addRow(settings.getLabel("outline.showScenes"), self.showScenes)
        self.form.addRow(settings.getLabel("outline.showSections"), self.showSections)

        # References
        # ==========

        title = settings.getLabel("outline.grpClass")
        section += 1
        self.sidebar.addButton(title, section)
        self.form.addGroupLabel(title, section)

        self.showCharacters = NSwitch(self, height=iPx)
        self.showPlot = NSwitch(self, height=iPx)
        self.showWorld = NSwitch(self, height=iPx)
        self.showObject = NSwitch(self, height=iPx)
        self.showEntity = NSwitch(self, height=iPx)
        self.showCustom = NSwitch(self, height=iPx)
        self.showMentions = NSwitch(self, height=iPx)

        self.form.addRow(settings.getLabel("outline.showCharacters"), self.showCharacters)
        self.form.addRow(settings.getLabel("outline.showPlot"), self.showPlot)
        self.form.addRow(settings.getLabel("outline.showWorld"), self.showWorld)
        self.form.addRow(settings.getLabel("outline.showObject"), self.showObject)
        self.form.addRow(settings.getLabel("outline.showEntity"), self.showEntity)
        self.form.addRow(settings.getLabel("outline.showCustom"), self.showCustom)
        self.form.addRow(settings.getLabel("outline.showMentions"), self.showMentions)

        # Finalise
        self.form.finalise()

    def loadSettings(self) -> None:
        """Populate the settings."""
        settings = self._settings

        # Documents
        self.showParts.setChecked(settings.getBool("outline.showParts"))
        self.showScenes.setChecked(settings.getBool("outline.showScenes"))
        self.showSections.setChecked(settings.getBool("outline.showSections"))

        # References
        self.showCharacters.setChecked(settings.getBool("outline.showCharacters"))
        self.showPlot.setChecked(settings.getBool("outline.showPlot"))
        self.showWorld.setChecked(settings.getBool("outline.showWorld"))
        self.showObject.setChecked(settings.getBool("outline.showObject"))
        self.showEntity.setChecked(settings.getBool("outline.showEntity"))
        self.showCustom.setChecked(settings.getBool("outline.showCustom"))
        self.showMentions.setChecked(settings.getBool("outline.showMentions"))

    def saveSettings(self) -> None:
        """Save the settings."""
        settings = self._settings

        # Documents
        settings.setValue("outline.showParts", self.showParts.isChecked())
        settings.setValue("outline.showScenes", self.showScenes.isChecked())
        settings.setValue("outline.showSections", self.showSections.isChecked())

        # References
        settings.setValue("outline.showCharacters", self.showCharacters.isChecked())
        settings.setValue("outline.showPlot", self.showPlot.isChecked())
        settings.setValue("outline.showWorld", self.showWorld.isChecked())
        settings.setValue("outline.showObject", self.showObject.isChecked())
        settings.setValue("outline.showEntity", self.showEntity.isChecked())
        settings.setValue("outline.showCustom", self.showCustom.isChecked())
        settings.setValue("outline.showMentions", self.showMentions.isChecked())


class GuiStoryOutlineTree(NTreeView):
    """GUI: Project Story Outline.

    A flat list of the partitions, chapters, scenes and sections of a
    novel, in story order, with a column for each type of reference
    enabled in the settings.
    """

    def __init__(self, parent: QWidget, settings: OutlineViewSettings) -> None:
        super().__init__(parent=parent)

        self._settings = settings
        self._model = OutlineModel()
        self._delegate = _OutlineDelegate(self)

        # Build State
        self._built = False
        self._lastHandle: str | None = None
        self._lastRevision = -1

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setUniformRowHeights(False)
        self.setAllColumnsShowFocus(True)
        self.setHeaderHidden(False)
        self.setDragEnabled(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.initViewport()
        self._disableNativeHighlight()

        if header := self.header():  # pragma: no branch
            header.setStretchLastSection(False)
            header.setMinimumSectionSize(60)
            header.setDefaultSectionSize(160)
            header.setSectionResizeMode(QtHeaderInteractive)
            header.setSectionResizeMode(OutlineModel.C_SYNOPSIS, QtHeaderStretch)
            header.resizeSection(OutlineModel.C_TITLE, 260)

        self._loadColumnState()

    ##
    #  Methods
    ##

    def initViewport(self) -> None:
        """Initialise viewport settings."""
        if CONFIG.hideVScroll:
            self.setVerticalScrollBarPolicy(QtScrollAlwaysOff)
        else:
            self.setVerticalScrollBarPolicy(QtScrollAsNeeded)
        if CONFIG.hideHScroll:
            self.setHorizontalScrollBarPolicy(QtScrollAlwaysOff)
        else:
            self.setHorizontalScrollBarPolicy(QtScrollAsNeeded)

    def updateTheme(self) -> None:
        """Update theme elements."""
        self._disableNativeHighlight()
        self._delegate.updateTheme()
        if viewport := self.viewport():  # pragma: no branch
            viewport.update()

    def _disableNativeHighlight(self) -> None:
        """Make the native row selection highlight transparent so it does
        not clash with the delegate's level-coloured selection box, which
        is drawn only around the text. Reapplied on theme changes as the
        palette is otherwise refreshed from the application palette.
        """
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Highlight, QtTransparent)
        self.setPalette(palette)

    def refresh(self, rootHandle: str | None, force: bool = False) -> None:
        """Rebuild the outline from the project index, but only if there
        is a genuine change since the last build, or if forced.
        """
        index = SHARED.project.index
        if force or not self._built or rootHandle != self._lastHandle or index.indexRevision != self._lastRevision:
            logger.info("Building story view '%s'", self._settings.name)
            settings = self._settings
            levels = {2}
            if settings.getBool("outline.showParts"):
                levels.add(1)
            if settings.getBool("outline.showScenes"):
                levels.add(3)
            if settings.getBool("outline.showSections"):
                levels.add(4)
            self._model.buildOutline(index, rootHandle, levels)

            worldKeys = []
            if settings.getBool("outline.showWorld"):
                worldKeys.append(nwKeyWords.WORLD_KEY)
            if settings.getBool("outline.showObject"):
                worldKeys.append(nwKeyWords.OBJECT_KEY)
            if settings.getBool("outline.showEntity"):
                worldKeys.append(nwKeyWords.ENTITY_KEY)
            self._delegate.setWorldKeys(worldKeys)

            self.setColumnHidden(OutlineModel.C_CHARS, not settings.getBool("outline.showCharacters"))
            self.setColumnHidden(OutlineModel.C_PLOT, not settings.getBool("outline.showPlot"))
            self.setColumnHidden(OutlineModel.C_WORLD, not worldKeys)
            self.setColumnHidden(OutlineModel.C_CUSTOM, not settings.getBool("outline.showCustom"))
            self.setColumnHidden(OutlineModel.C_MENTION, not settings.getBool("outline.showMentions"))
            self._built = True
            self._lastHandle = rootHandle
            self._lastRevision = index.indexRevision

    def saveColumnState(self) -> None:
        """Save the column order and widths to the settings object. Hidden
        columns keep their last known width.
        """
        if header := self.header():  # pragma: no branch
            previous = self._settings.getState("columns")
            previous = previous if isinstance(previous, dict) else {}
            state = {}
            for visual in range(header.count()):
                column = header.logicalIndex(visual)
                key = COLUMN_KEYS[column]
                if self.isColumnHidden(column):
                    width = previous.get(key, header.defaultSectionSize())
                else:
                    width = header.sectionSize(column)
                state[key] = width
            self._settings.setState("columns", state)

    def clear(self) -> None:
        """Clear the outline."""
        self._model.clear()
        self._built = False
        self._lastHandle = None
        self._lastRevision = -1

    ##
    #  Overrides
    ##

    def drawRow(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint the level-coloured box and border wrapping the row text
        before the native cell painting. The native selection highlight is
        transparent (see _disableNativeHighlight), so the selection is
        shown by the box instead.
        """
        if node := self._model.node(index):  # pragma: no branch
            first = index.sibling(index.row(), OutlineModel.C_TITLE)
            selected = self._isRowSelected(first)
            block = option.rect.adjusted(0, ROW_PAD, -ROW_PAD, -ROW_PAD)
            block.setLeft(self.visualRect(first).left())
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(option.rect, self.palette().base())
            painter.setPen(node.style.border)
            painter.setBrush(node.style.highlight if selected else node.style.background)
            painter.drawRoundedRect(block.adjusted(0, 0, -1, -1), ROW_RADIUS, ROW_RADIUS)
            painter.restore()

        super().drawRow(painter, option, index)

    def _loadColumnState(self) -> None:
        """Load the column order and widths from the settings object. The
        title column is always first, and unknown columns are skipped.
        """
        state = self._settings.getState("columns")
        if isinstance(state, dict) and (header := self.header()):
            columns = {v: k for k, v in COLUMN_KEYS.items()}
            visual = 1
            for key, width in state.items():
                if (column := columns.get(key)) is None:
                    logger.warning("Unknown outline column '%s'", key)
                    continue
                if isinstance(width, int) and width >= header.minimumSectionSize():
                    header.resizeSection(column, width)
                if column != OutlineModel.C_TITLE:
                    header.moveSection(header.visualIndex(column), visual)
                    visual += 1

    def _isRowSelected(self, index: QModelIndex) -> bool:
        """Return whether the given row index is selected."""
        return bool(sm.isSelected(index)) if (sm := self.selectionModel()) else False


class _OutlineDelegate(QStyledItemDelegate):
    """GUI: Story Outline Row Delegate.

    Paints each row over three lines of height.
    """

    __slots__ = (
        "_boldFormat",
        "_fm",
        "_fmB",
        "_keyLabels",
        "_lineHeight",
        "_margin",
        "_rowHeight",
        "_textCol",
        "_worldKeys",
        "_wrapOption",
    )

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self._margin = 8
        self._rowHeight = 0
        self._lineHeight = 0
        self._worldKeys: list[str] = []
        self._boldFormat = QTextCharFormat()
        self._wrapOption = QTextOption()
        self._wrapOption.setWrapMode(QTextOption.WrapMode.WordWrap)
        self._keyLabels = {
            k: trConst(nwLabels.KEY_NAME[k])
            for k in (
                nwKeyWords.POV_KEY,
                nwKeyWords.FOCUS_KEY,
                nwKeyWords.CHAR_KEY,
                nwKeyWords.PLOT_KEY,
                nwKeyWords.TIME_KEY,
                nwKeyWords.WORLD_KEY,
                nwKeyWords.OBJECT_KEY,
                nwKeyWords.ENTITY_KEY,
            )
        }
        self.updateTheme()

    def setWorldKeys(self, keys: list[str]) -> None:
        """Set the keywords to show in the world column, in order."""
        self._worldKeys = keys

    def updateTheme(self) -> None:
        """Refresh the cached theme fonts and colours."""
        self._fm = QFontMetrics(SHARED.theme.guiFont)
        self._fmB = QFontMetrics(SHARED.theme.guiFontB)
        self._lineHeight = self._fmB.height() + 2 * self._margin + 2 * ROW_PAD
        self._rowHeight = self._lineHeight + 2 * self._fm.height()
        self._textCol = QApplication.palette().text().color()
        self._boldFormat.setFont(SHARED.theme.guiFontB)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return the row height: one line for partitions, three lines for
        all other rows.
        """
        model = index.model()
        if isinstance(model, OutlineModel) and (node := model.node(index)) and node.level == 1:
            return QSize(option.rect.width(), self._lineHeight)
        return QSize(option.rect.width(), self._rowHeight)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Paint a story outline row."""
        model = index.model()
        if not isinstance(model, OutlineModel) or not (node := model.node(index)):
            super().paint(painter, option, index)
            return

        rect = option.rect

        painter.save()
        painter.setClipRect(rect)
        painter.setPen(self._textCol)

        pad = ROW_PAD + self._margin
        x = rect.x() + pad
        y = rect.y() + pad
        w = max(0, rect.width() - 2 * pad)
        h = max(0, rect.height() - 2 * pad)

        if node.level == 1:
            if index.column() == OutlineModel.C_TITLE:
                painter.setFont(SHARED.theme.guiFontB)
                title = self._fmB.elidedText(node.title, QtElideRight, w)
                painter.drawText(QRect(x, y, w, h), LINE_FLAGS, title)
            painter.restore()
            return

        match index.column():
            case OutlineModel.C_TITLE:
                hTitle = self._fmB.height()
                hLine = self._fm.height()

                painter.setFont(SHARED.theme.guiFontB)
                title = self._fmB.elidedText(node.title, QtElideRight, w)
                painter.drawText(QRect(x, y, w, hTitle), LINE_FLAGS, title)

                painter.setFont(SHARED.theme.guiFont)
                label = self._fm.elidedText(node.label, QtElideRight, w)
                painter.drawText(QRect(x, y + hTitle, w, hLine), LINE_FLAGS, label)

                counts = self._fm.elidedText(node.counts, QtElideRight, w)
                painter.drawText(QRect(x, y + hTitle + hLine, w, hLine), LINE_FLAGS, counts)

            case OutlineModel.C_CHARS:
                hLine = self._fm.height()
                maxX = x + w

                # Line 1: Point of View and Focus
                xPos = x
                for key in (nwKeyWords.POV_KEY, nwKeyWords.FOCUS_KEY):
                    if not (value := node.refs(key)):
                        continue
                    if xPos > x:
                        painter.setFont(SHARED.theme.guiFont)
                        sep = f"  {nwUnicode.U_BULL}  "
                        painter.drawText(QRect(xPos, y, maxX - xPos, hLine), LINE_FLAGS, sep)
                        xPos += self._fm.horizontalAdvance(sep)
                    xPos = self._paintLabelled(painter, xPos, y, maxX, hLine, self._keyLabels[key], value)

                # Line 2: Characters
                self._paintWrapped(painter, x, y + hLine, w, h - hLine, node, nwKeyWords.CHAR_KEY)

            case OutlineModel.C_PLOT:
                hLine = self._fm.height()

                # Line 1: Plot
                if value := node.refs(nwKeyWords.PLOT_KEY):
                    label = self._keyLabels[nwKeyWords.PLOT_KEY]
                    self._paintLabelled(painter, x, y, x + w, hLine, label, value)

                # Line 2: Timeline
                self._paintWrapped(painter, x, y + hLine, w, h - hLine, node, nwKeyWords.TIME_KEY)

            case OutlineModel.C_SYNOPSIS:
                painter.setFont(SHARED.theme.guiFont)
                painter.drawText(QRect(x, y, w, h), WRAP_FLAGS, node.synopsis)

            case OutlineModel.C_WORLD:
                hLine = self._fm.height()
                for i, key in enumerate(self._worldKeys):
                    if value := node.refs(key):
                        self._paintLabelled(painter, x, y + i * hLine, x + w, hLine, self._keyLabels[key], value)

            case OutlineModel.C_CUSTOM:
                painter.setFont(SHARED.theme.guiFont)
                painter.drawText(QRect(x, y, w, h), WRAP_FLAGS, node.refs(nwKeyWords.CUSTOM_KEY))

            case OutlineModel.C_MENTION:  # pragma: no branch
                painter.setFont(SHARED.theme.guiFont)
                painter.drawText(QRect(x, y, w, h), WRAP_FLAGS, node.refs(nwKeyWords.MENTION_KEY))

        painter.restore()

    def _paintLabelled(self, painter: QPainter, x: int, y: int, maxX: int, h: int, label: str, value: str) -> int:
        """Paint a bold label followed by a regular value on one line,
        and return the x position after the value.
        """
        text = f"{label}: "
        painter.setFont(SHARED.theme.guiFontB)
        painter.drawText(QRect(x, y, maxX - x, h), LINE_FLAGS, text)
        x += self._fmB.horizontalAdvance(text)

        painter.setFont(SHARED.theme.guiFont)
        value = self._fm.elidedText(value, QtElideRight, maxX - x)
        painter.drawText(QRect(x, y, maxX - x, h), LINE_FLAGS, value)
        return x + self._fm.horizontalAdvance(value)

    def _paintWrapped(self, painter: QPainter, x: int, y: int, w: int, h: int, node: OutlineNode, key: str) -> None:
        """Paint a bold label followed by a regular value wrapped over
        the full width, if the node has references for the key.
        """
        if value := node.refs(key):
            label = f"{self._keyLabels[key]}:"
            bold = QTextLayout.FormatRange()
            bold.start = 0
            bold.length = len(label)
            bold.format = self._boldFormat

            layout = QTextLayout(f"{label} {value}", SHARED.theme.guiFont)
            layout.setFormats([bold])
            layout.setTextOption(self._wrapOption)
            layout.beginLayout()
            yPos = 0.0
            while yPos < h and (line := layout.createLine()).isValid():
                line.setLineWidth(w)
                line.setPosition(QPointF(0.0, yPos))
                yPos += line.height()
            layout.endLayout()
            layout.draw(painter, QPointF(x, y))
