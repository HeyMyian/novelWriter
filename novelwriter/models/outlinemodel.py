"""
novelWriter - Outline Model
===========================

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

from typing import TYPE_CHECKING, NamedTuple

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor

from novelwriter import SHARED
from novelwriter.constants import nwKeyWords, nwLabels, nwStats, nwStyles, nwUnicode, trConst, trStats
from novelwriter.types import QtTransparent

if TYPE_CHECKING:
    from novelwriter.core.index import Index
    from novelwriter.core.indexdata import IndexHeading
    from novelwriter.core.item import ProjectItem

logger = logging.getLogger(__name__)

NODE_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class _TrCache(NamedTuple):
    sWords: str
    sChars: str


class NodeStyle(NamedTuple):
    """Core: Outline Node Style Class."""

    border: QColor
    background: QColor
    highlight: QColor


BLANK_STYLE = NodeStyle(QtTransparent, QtTransparent, QtTransparent)


class OutlineNode:
    """Core: Outline Model Node Class.

    A single row in the story outline, representing one partition,
    chapter, scene or section heading. The outline is entirely rebuilt
    on demand from the project index, so nodes hold plain copies of the
    values needed for display rather than a live reference to the index
    data.
    """

    __slots__ = (
        "_counts",
        "_document",
        "_handle",
        "_heading",
        "_item",
        "_key",
        "_level",
        "_refs",
        "_style",
        "_title",
        "_tr",
    )

    def __init__(
        self,
        handle: str,
        key: str,
        item: ProjectItem | None,
        heading: IndexHeading | None,
        tr: _TrCache,
        style: NodeStyle,
    ) -> None:
        self._handle = handle
        self._key = key
        self._item = item
        self._heading: IndexHeading | None = heading
        self._tr: _TrCache = tr

        # Parsed Data
        self._level = 0
        self._title = ""
        self._document = ""
        self._counts = ""
        self._refs: dict[str, str] = {}
        self._style = style

        self.refresh()

    ##
    #  Properties
    ##

    @property
    def handle(self) -> str:
        """The handle of the document the heading belongs to."""
        return self._handle

    @property
    def key(self) -> str:
        """The heading key within its document."""
        return self._key

    @property
    def title(self) -> str:
        """The heading title."""
        return self._title

    @property
    def level(self) -> int:
        """The heading level."""
        return self._level

    @property
    def label(self) -> str:
        """The name of the document the heading belongs to."""
        return self._document

    @property
    def counts(self) -> str:
        """The word and character counts of the heading."""
        return self._counts

    @property
    def synopsis(self) -> str:
        """The synopsis of the heading."""
        if hItem := self._heading:
            return hItem.synopsis
        return ""

    @property
    def style(self) -> NodeStyle:
        """The style for the heading's structural level."""
        return self._style

    ##
    #  Data Access
    ##

    def refs(self, keyword: str) -> str:
        """Return the references of the heading for a keyword."""
        return self._refs.get(keyword, "")

    ##
    #  Data Maintenance
    ##

    def refresh(self) -> None:
        """Refresh data values."""
        tr = self._tr
        if h := self._heading:
            self._level = nwStyles.H_LEVEL.get(h.level, 0)
            self._title = h.title
            self._counts = f"{h.wordCount:n} {tr.sWords}  {nwUnicode.U_BULL}  {h.charCount:n} {tr.sChars}"

            self._refs = {k: ", ".join(v) for k, v in h.getReferences().items() if v}

        if i := self._item:
            self._document = i.itemName


class OutlineModel(QAbstractTableModel):
    """Core: Outline Model Class.

    A flat list of partition, chapter, scene and section headings for a
    single novel root, in story order, built fresh from the project index
    whenever buildOutline is called.
    """

    __slots__ = ("_headers", "_labels", "_nodes", "_styles")

    C_TITLE = 0
    C_CHARS = 1
    C_PLOT = 2
    C_WORLD = 3
    C_CUSTOM = 4
    C_MENTION = 5
    C_SYNOPSIS = 6

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
            self.tr("Story"),
            trConst(nwLabels.KEY_NAME[nwKeyWords.CHAR_KEY]),
            trConst(nwLabels.KEY_NAME[nwKeyWords.PLOT_KEY]),
            self.tr("World"),
            trConst(nwLabels.KEY_NAME[nwKeyWords.CUSTOM_KEY]),
            trConst(nwLabels.KEY_NAME[nwKeyWords.MENTION_KEY]),
            self.tr("Synopsis"),
        ]
        self._labels = _TrCache(
            sWords=trStats(nwLabels.STATS_NAME[nwStats.WORDS]),
            sChars=trStats(nwLabels.STATS_NAME[nwStats.CHARS]),
        )

        # Colours
        theme = SHARED.theme
        self._styles: dict[int, NodeStyle] = {}
        for key in nwStyles.H_LEVEL.values():
            color = theme.getStructureColor(key)
            border = QColor(color)
            border.setAlphaF(0.7)
            background = QColor(color)
            background.setAlphaF(0.1)
            highlight = QColor(color)
            highlight.setAlphaF(0.2)
            self._styles[key] = NodeStyle(border, background, highlight)

        self._nodes: list[OutlineNode] = []

    def __del__(self) -> None:  # pragma: no cover
        """Class destructor."""
        logger.debug("Delete: OutlineModel")

    ##
    #  Model Interface
    ##

    def rowCount(self, parent: QModelIndex) -> int:
        """Return the number of rows."""
        return 0 if parent.isValid() else len(self._nodes)

    def columnCount(self, parent: QModelIndex) -> int:
        """Return the number of columns."""
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> None:
        """Return display data for a node."""
        return

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole) -> str | None:
        """Return the header labels for the outline columns."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section] if 0 <= section < len(self._headers) else None
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Return flags for a node."""
        return NODE_FLAGS if index.isValid() else Qt.ItemFlag.NoItemFlags

    ##
    #  Data Access
    ##

    def node(self, index: QModelIndex) -> OutlineNode | None:
        """Return the node for a given model index."""
        if index.isValid() and 0 <= (row := index.row()) < len(self._nodes):
            return self._nodes[row]
        return None

    ##
    #  Methods
    ##

    def clear(self) -> None:
        """Clear the outline."""
        self.beginResetModel()
        self._nodes = []
        self.endResetModel()

    def buildOutline(self, index: Index, rootHandle: str | None, levels: set[int]) -> None:
        """Rebuild the outline from the project index, including only
        headings of the given levels.
        """
        self.beginResetModel()
        nodes: list[OutlineNode] = []
        for tHandle, sTitle, hItem in index.iterNovelStructure(rHandle=rootHandle):
            level = nwStyles.H_LEVEL.get(hItem.level, 0)
            if level not in levels:
                continue
            if (nwItem := SHARED.project.tree[tHandle]) is None:
                continue
            style = self._styles.get(level, BLANK_STYLE)
            nodes.append(OutlineNode(tHandle, sTitle, nwItem, hItem, self._labels, style))

        self._nodes = nodes
        self.endResetModel()
