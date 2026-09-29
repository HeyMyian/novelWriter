"""
novelWriter - Outline Model Tester
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

import pytest

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtTest import QAbstractItemModelTester

from novelwriter import SHARED
from novelwriter.constants import nwKeyWords
from novelwriter.models.outlinemodel import BLANK_STYLE, NODE_FLAGS, OutlineModel, OutlineNode
from novelwriter.types import QtDisplayRole


@pytest.mark.core
def testOutlineModel_ModelTest(nwGUI, prjLipsum):
    """Run the Qt model tester on the model."""
    model = OutlineModel()
    QAbstractItemModelTester(model)

    assert nwGUI.openProject(prjLipsum)
    model.buildOutline(SHARED.project.index, None, {1, 2, 3, 4})
    QAbstractItemModelTester(model)


@pytest.mark.core
def testOutlineModel_Interface(nwGUI, prjLipsum):
    """Test the outline model interface."""
    assert nwGUI.openProject(prjLipsum)
    index = SHARED.project.index
    root = QModelIndex()

    model = OutlineModel()
    assert model.rowCount(root) == 0
    assert model.columnCount(root) == 7

    # All levels
    model.buildOutline(index, None, {1, 2, 3, 4})
    assert model.rowCount(root) == 12
    assert model.rowCount(model.index(0, 0)) == 0
    assert model.columnCount(model.index(0, 0)) == 0

    # Filtered levels keep the story order
    model.buildOutline(index, None, {2})
    assert model.rowCount(root) == 3
    assert [model.node(model.index(r, 0)).title for r in range(3)] == [  # type: ignore
        "Prologue",
        "Chapter One",
        "Chapter Two",
    ]

    # Headers
    horizontal = Qt.Orientation.Horizontal
    assert model.headerData(OutlineModel.C_TITLE, horizontal, QtDisplayRole) == "Story"
    assert model.headerData(OutlineModel.C_CHARS, horizontal, QtDisplayRole) == "Characters"
    assert model.headerData(OutlineModel.C_WORLD, horizontal, QtDisplayRole) == "World"
    assert model.headerData(OutlineModel.C_MENTION, horizontal, QtDisplayRole) == "Mentions"
    assert model.headerData(OutlineModel.C_SYNOPSIS, horizontal, QtDisplayRole) == "Synopsis"
    assert model.headerData(99, horizontal, QtDisplayRole) is None
    assert model.headerData(0, Qt.Orientation.Vertical, QtDisplayRole) is None
    assert model.headerData(0, horizontal, Qt.ItemDataRole.ToolTipRole) is None

    # Data and flags
    assert model.data(model.index(0, 0), QtDisplayRole) is None
    assert model.flags(model.index(0, 0)) == NODE_FLAGS
    assert model.flags(root) == Qt.ItemFlag.NoItemFlags

    # Nodes
    assert model.node(root) is None
    assert model.node(model.createIndex(99, 0)) is None

    node = model.node(model.index(1, 0))
    assert isinstance(node, OutlineNode)
    assert node.handle == "fb609cd8319dc"
    assert node.key == "T0001"
    assert node.title == "Chapter One"
    assert node.level == 2
    assert node.label == "Chapter One"
    assert node.counts == "67 Words  •  419 Characters"
    assert node.synopsis.startswith("Lorem ipsum dolor sit amet")
    assert node.style is not BLANK_STYLE
    assert node.refs(nwKeyWords.POV_KEY) == "Bod"
    assert node.refs(nwKeyWords.MENTION_KEY) == ""

    # A node without a heading or an item is blank
    blank = OutlineNode("", "", None, None, model._labels, BLANK_STYLE)
    assert blank.level == 0
    assert blank.title == ""
    assert blank.label == ""
    assert blank.synopsis == ""

    # Clear the model
    model.clear()
    assert model.rowCount(root) == 0
