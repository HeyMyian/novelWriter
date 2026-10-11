"""
novelWriter - GUI Document Panes
================================

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

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QSplitter, QVBoxLayout, QWidget

from novelwriter import CONFIG, SHARED
from novelwriter.common import formatFileFilter
from novelwriter.editor.editor import GuiDocEditor
from novelwriter.editor.viewer import GuiDocViewer
from novelwriter.editor.viewerpanel import GuiDocViewerPanel
from novelwriter.enum import nwDocMode, nwView

if TYPE_CHECKING:
    from novelwriter.guimain import GuiMain

logger = logging.getLogger(__name__)


class GuiDocPanes(QWidget):
    """Gui Widget: Document Panes."""

    def __init__(self, mainGui: GuiMain) -> None:
        super().__init__(mainGui)

        self.mainGui = mainGui

        # Internal State
        self._switchingDocument = False

        # Components
        self.docEditor = GuiDocEditor(self)
        self.docViewer = GuiDocViewer(self)
        self.docViewerPanel = GuiDocViewerPanel(self)

        # Viewer Splitter
        self.splitView = QSplitter(Qt.Orientation.Vertical, self)
        self.splitView.addWidget(self.docViewer)
        self.splitView.addWidget(self.docViewerPanel)
        self.splitView.setHandleWidth(4)
        self.splitView.setOpaqueResize(False)
        self.splitView.setSizes(CONFIG.viewPanePos)
        self.splitView.setCollapsible(0, False)
        self.splitView.setCollapsible(1, False)

        # Main Splitter
        self.splitMain = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitMain.addWidget(self.docEditor)
        self.splitMain.addWidget(self.splitView)
        self.splitMain.setOpaqueResize(False)
        self.splitMain.setHandleWidth(4)
        self.splitMain.setCollapsible(0, False)
        self.splitMain.setCollapsible(1, False)

        # Editor / Viewer Default State
        self.splitView.setVisible(False)
        self.docEditor.closeSearch()

        # Assemble
        self.outerBox = QVBoxLayout()
        self.outerBox.addWidget(self.splitMain)
        self.outerBox.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.outerBox)

        # Connect Signals
        SHARED.indexAvailable.connect(self.docViewerPanel.indexHasAppeared)
        SHARED.indexChangedRefs.connect(self.docViewerPanel.updateChangedRefs)
        SHARED.indexChangedTags.connect(self.docEditor.updateChangedTags)
        SHARED.indexChangedTags.connect(self.docViewer.updateChangedTags)
        SHARED.indexChangedTags.connect(self.docViewerPanel.updateChangedTags)
        SHARED.indexCleared.connect(self.docViewerPanel.indexWasCleared)
        SHARED.projectItemChanged.connect(self.docEditor.onProjectItemChanged)
        SHARED.projectItemChanged.connect(self.docViewer.onProjectItemChanged)
        SHARED.projectItemChanged.connect(self.docViewerPanel.onProjectItemChanged)
        SHARED.spellLanguageChanged.connect(self.docEditor.processSpellCheckChange)
        SHARED.statusLabelsChanged.connect(self.docViewerPanel.updateStatusLabels)

        self.docEditor.closeEditorRequest.connect(self.closeDocEditor)
        self.docEditor.loadDocumentTagRequest.connect(self._followTag)
        self.docEditor.openDocumentRequest.connect(self.openDocumentInMode)
        self.docEditor.requestNextDocument.connect(self.openNextDocument)

        self.docViewer.closeDocumentRequest.connect(self.closeDocViewer)
        self.docViewer.documentLoaded.connect(self.docViewerPanel.updateHandle)
        self.docViewer.loadDocumentTagRequest.connect(self._followTag)
        self.docViewer.openDocumentRequest.connect(self.openDocumentInMode)
        self.docViewer.reloadDocumentRequest.connect(self._reloadViewer)
        self.docViewer.togglePanelVisibility.connect(self._toggleViewerPanelVisibility)

        self.docViewerPanel.loadDocumentTagRequest.connect(self._followTag)
        self.docViewerPanel.openDocumentRequest.connect(self.openDocumentInMode)

    ##
    #  Class Methods
    ##

    def openProjectTasks(self) -> None:
        """Run open project tasks, and restore the last open documents."""
        self.docEditor.toggleSpellCheck(SHARED.project.data.spellCheck)
        self.docViewerPanel.openProjectTasks()

        # If no document was recorded, open the first one found
        lastEdited = SHARED.project.data.getLastHandle("editor")
        if lastEdited is None:
            for nwItem in SHARED.project.tree:
                if nwItem and nwItem.isFileType():
                    lastEdited = nwItem.itemHandle
                    break

        if lastEdited is not None:
            self.openDocument(lastEdited, doScroll=True)

        if lastViewed := SHARED.project.data.getLastHandle("viewer"):
            self.viewDocument(lastViewed)

    def closeProjectTasks(self) -> None:
        """Run close project tasks."""
        self.closeDocument()
        self.docViewer.clearNavHistory()
        self.closeViewerPanel(byUser=False)
        self.docViewerPanel.closeProjectTasks()

    ##
    #  Document Methods
    ##

    def closeDocument(self) -> None:
        """Close the document and clear the editor and title field."""
        if SHARED.hasProject:
            # Disable focus mode if it is active
            if SHARED.focusMode:
                SHARED.setFocusMode(False)
            self.saveDocument()
            self.docEditor.clearEditor()

    def openDocument(
        self,
        tHandle: str | None,
        tLine: int | None = None,
        sTitle: str | None = None,
        changeFocus: bool = True,
        doScroll: bool = False,
    ) -> bool:
        """Open a specific document, optionally at a given line."""
        if not (SHARED.hasProject and tHandle):
            logger.error("Nothing to open")
            return False

        if self._switchingDocument:
            logger.debug("Ignoring re-entrant request to open '%s'", tHandle)
            return False

        if sTitle and tLine is None and (hItem := SHARED.project.index.getItemHeading(tHandle, sTitle)):
            tLine = hItem.line

        self.mainGui.changeView(nwView.EDITOR)
        if tHandle == self.docEditor.docHandle:
            self.docEditor.setCursorLine(tLine)
        else:
            self._switchingDocument = True
            try:
                self.closeDocument()
                if self.docEditor.loadText(tHandle, tLine):
                    self.mainGui.projView.setSelectedHandle(tHandle, doScroll=doScroll)
                else:
                    return False
            finally:
                self._switchingDocument = False

        if changeFocus:
            self.docEditor.setFocus()

        return True

    def saveDocument(self, force: bool = False) -> None:
        """Save the current documents."""
        if SHARED.hasProject:
            self.docEditor.saveCursorPosition()
            if force or self.docEditor.docChanged:
                self.docEditor.saveText()

    def importDocument(self) -> bool:
        """Import the text contained in an out-of-project text file, and
        insert the text into the currently open document.
        """
        if not SHARED.hasProject:
            logger.error("No project open")
            return False

        lastPath = CONFIG.lastPath("import")
        ffilter = formatFileFilter(["*.txt", "*.md", "*"])
        loadFile, _ = QFileDialog.getOpenFileName(self, self.tr("Import File"), str(lastPath), filter=ffilter)
        if not loadFile:
            return False

        if loadFile.strip() == "":
            return False

        text = None
        try:
            with open(loadFile, mode="rt", encoding="utf-8") as inFile:
                text = inFile.read()
            CONFIG.setLastPath("import", loadFile)
        except Exception as exc:
            SHARED.error(self.tr("Could not read file. The file must be an existing text file."), exc=exc)
            return False

        if self.docEditor.docHandle is None:
            SHARED.error(self.tr("Please open a document to import the text file into."))
            return False

        if not self.docEditor.isEmpty:
            msgYes = SHARED.question(
                self.tr(
                    "Importing the file will overwrite the current content of the document. Do you want to proceed?"
                )
            )
            if not msgYes:
                return False

        self.docEditor.replaceText(text)

        return True

    def viewDocument(self, tHandle: str | None = None, sTitle: str | None = None) -> bool:
        """Load a document for viewing in the view panel."""
        if not SHARED.hasProject:
            logger.error("No project open")
            return False

        if tHandle is None:
            logger.debug("Viewing document, but no handle provided")

            if self.docEditor.hasFocus():
                tHandle = self.docEditor.docHandle

            if tHandle is not None:
                self.saveDocument()
            else:
                tHandle = self.mainGui.projView.getSelectedHandle()

            if tHandle is None:
                tHandle = SHARED.project.data.getLastHandle("viewer")

            if tHandle is None:
                logger.debug("No document to view, giving up")
                return False

        # Make sure main tab is in Editor view
        self.mainGui.changeView(nwView.EDITOR)

        # If we're loading the document in the editor, it may need to be saved
        if tHandle == self.docEditor.docHandle and self.docEditor.docChanged:
            self.saveDocument()

        logger.debug("Viewing document with handle '%s'", tHandle)
        updateHistory = tHandle != self.docViewer.docHandle
        if self.docViewer.loadText(tHandle, updateHistory=updateHistory):
            if not self.splitView.isVisible():
                cursorVisible = self.docEditor.cursorIsVisible()
                self.splitView.setVisible(True)
                self.splitMain.setSizes([1, 1])
                self.docViewerPanel.setVisible(CONFIG.showViewerPanel)

                # Since editor width changes, we need to make sure we
                # restore cursor visibility in the editor. See #1302
                if cursorVisible:
                    self.docEditor.ensureCursorVisible(centre=False)

            if sTitle:
                self.docViewer.navigateTo(f"#{tHandle}:{sTitle}")

        return True

    def closeViewerPanel(self, byUser: bool = True) -> bool:
        """Close the document view panel."""
        self.docViewer.clearViewer()
        if byUser:
            # Only reset the last handle if the user called this
            SHARED.project.data.setLastHandle(None, "viewer")

        cursorVisible = self.docEditor.cursorIsVisible()

        self.splitView.setVisible(False)

        # Since editor width changes, we need to make sure we restore
        # cursor visibility in the editor. See #1302
        if cursorVisible:
            self.docEditor.ensureCursorVisible(centre=False)

        return not self.splitView.isVisible()

    ##
    #  Public Slots
    ##

    @pyqtSlot()
    def closeDocEditor(self) -> None:
        """Close the document editor. This does not hide the editor."""
        self.closeDocument()
        SHARED.project.data.setLastHandle(None, "editor")

    @pyqtSlot()
    def closeDocViewer(self) -> None:
        """Close the document viewer."""
        self.closeViewerPanel()

    @pyqtSlot()
    def forceSaveDocument(self) -> None:
        """Save document even of it has not changed."""
        self.saveDocument(force=True)

    @pyqtSlot(str, nwDocMode, str, bool)
    def openDocumentInMode(self, tHandle: str, mode: nwDocMode, sTitle: str, setFocus: bool) -> None:
        """Handle an open document request."""
        if tHandle is not None:
            if mode == nwDocMode.EDIT:
                self.openDocument(tHandle, sTitle=sTitle, changeFocus=setFocus)
            elif mode == nwDocMode.VIEW:
                self.viewDocument(tHandle=tHandle, sTitle=sTitle)
            else:  # pragma: no cover
                pass

    @pyqtSlot(str, int, int, bool)
    def openDocumentSelection(self, tHandle: str, selStart: int, selLength: int, changeFocus: bool) -> None:
        """Open a document and select a section of the text."""
        if self.openDocument(tHandle, changeFocus=changeFocus):
            self.docEditor.setCursorSelection(selStart, selLength)

    @pyqtSlot(str, bool, bool)
    def openNextDocument(self, tHandle: str, wrapAround: bool, goBack: bool) -> None:
        """Open the next (or previous) document in the project tree,
        next to the document with the given handle. Stop when reaching
        the edge unless the wrapAround flag is set.
        """
        if SHARED.hasProject and (allDocs := SHARED.project.tree.allDocs()):
            try:
                currIdx = allDocs.index(tHandle)
                nHandle = (
                    ((allDocs[-1] if wrapAround else None) if currIdx == 0 else allDocs[currIdx - 1])
                    if goBack
                    else ((allDocs[0] if wrapAround else None) if currIdx == len(allDocs) - 1 else allDocs[currIdx + 1])
                )
                if nHandle is not None:
                    self.openDocument(nHandle, tLine=(-1 if goBack else 1), doScroll=True)
            except Exception:
                logger.error("Could not find next document for '%s'", tHandle)

    ##
    #  Private Slots
    ##

    @pyqtSlot(str, nwDocMode)
    def _followTag(self, tag: str, mode: nwDocMode) -> None:
        """Follow a tag after user interaction with a link."""
        tHandle, sTitle = SHARED.project.index.getTagSource(tag)
        if tHandle is None:
            SHARED.error(
                self.tr(
                    "Could not find the reference for tag '{0}'. It either doesn't "
                    "exist, or the index is out of date. The index can be updated "
                    "from the Tools menu, or by pressing {1}."
                ).format(tag, "F9")
            )
        else:
            if mode == nwDocMode.EDIT:
                self.openDocument(tHandle, sTitle=sTitle)
            elif mode == nwDocMode.VIEW:
                self.viewDocument(tHandle=tHandle, sTitle=sTitle)
            else:  # pragma: no cover
                pass

    @pyqtSlot()
    def _reloadViewer(self) -> None:
        """Reload the document in the viewer."""
        if self.docEditor.docHandle == self.docViewer.docHandle:
            # If the two panels have the same document, save any changes in the editor
            self.saveDocument()
        self.docViewer.reloadText()

    @pyqtSlot()
    def _toggleViewerPanelVisibility(self) -> None:
        """Toggle the visibility of the document viewer panel."""
        CONFIG.showViewerPanel = not CONFIG.showViewerPanel
        self.docViewerPanel.setVisible(CONFIG.showViewerPanel)
