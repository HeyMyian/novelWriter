"""
novelWriter - Story View Settings
=================================

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

import json
import logging
import uuid

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

from novelwriter.common import jsonEncode, safeExists
from novelwriter.constants import nwFiles
from novelwriter.error import logException

if TYPE_CHECKING:
    from novelwriter.core.project import NWProject

logger = logging.getLogger(__name__)

T_BuildValue = str | int | float | bool

# The Settings Template
# =====================
# Each entry contains a tuple on the form: (type, default)

# fmt: off
SETTINGS_TEMPLATE: dict[str, tuple[type, T_BuildValue]] = {
    "common.showScenes":   (bool, True),
    "common.showSections": (bool, False),
}

SETTINGS_LABELS = {
    "common.showScenes":   QT_TRANSLATE_NOOP("StoryViews", "Show scenes"),
    "common.showSections": QT_TRANSLATE_NOOP("StoryViews", "Show sections"),
}
# fmt: on


class StoryViewSettings:
    """Story: Story View Settings Class.

    This class manages the build settings for a Manuscript build job.
    The settings can be packed/unpacked to/from a dictionary for JSON.
    """

    __slots__ = ("_changed", "_kind", "_name", "_order", "_settings", "_uuid")

    def __init__(self) -> None:
        self._name = ""
        self._uuid = str(uuid.uuid4())
        self._order = 0
        self._settings = {k: v[1] for k, v in SETTINGS_TEMPLATE.items()}
        self._changed = False
        self._kind = ()

    @classmethod
    def fromDict(cls, data: dict) -> StoryViewSettings:
        """Create a build settings object from a dict."""
        new = cls()
        new.unpack(data)
        return new

    ##
    #  Properties
    ##

    @property
    def name(self) -> str:
        """Return the story view name."""
        return self._name

    @property
    def viewID(self) -> str:
        """Return the view ID as a UUID."""
        return self._uuid

    @property
    def order(self) -> int:
        """Return the story view order."""
        return self._order

    @property
    def changed(self) -> bool:
        """The changed status of the story view."""
        return self._changed

    ##
    #  Setters
    ##

    def setName(self, name: str) -> None:
        """Set the story view display name."""
        self._name = str(name)

    def setOrder(self, value: int) -> None:
        """Set the story view order."""
        if isinstance(value, int):
            self._order = value

    def setValue(self, key: str, value: T_BuildValue) -> None:
        """Set a specific value for a story view setting."""
        if (d := SETTINGS_TEMPLATE.get(key)) and len(d) == 2 and isinstance(value, d[0]):
            self._changed |= value != self._settings[key]
            self._settings[key] = value

    def setKind(self, kind: str) -> None:
        """Set the story view kind."""
        self._kind = ("common.", f"{kind!s}.")

    ##
    #  Getters
    ##

    @staticmethod
    def getLabel(key: str) -> str:
        """Extract the GUI label for a specific setting."""
        return QCoreApplication.translate("StoryViews", SETTINGS_LABELS.get(key, "ERROR"))

    def getStr(self, key: str) -> str:
        """Type safe value access for strings."""
        value = self._settings.get(key, SETTINGS_TEMPLATE.get(key, (None, None))[1])
        return str(value)

    def getBool(self, key: str) -> bool:
        """Type safe value access for bools."""
        value = self._settings.get(key, SETTINGS_TEMPLATE.get(key, (None, None))[1])
        return bool(value)

    def getInt(self, key: str) -> int:
        """Type safe value access for integers."""
        value = self._settings.get(key, SETTINGS_TEMPLATE.get(key, (None, None))[1])
        return int(value) if isinstance(value, int | float) else 0

    def getFloat(self, key: str) -> float:
        """Type safe value access for floats."""
        value = self._settings.get(key, SETTINGS_TEMPLATE.get(key, (None, None))[1])
        return float(value) if isinstance(value, int | float) else 0.0

    ##
    #  Methods
    ##

    def pack(self) -> dict:
        """Pack all content into a JSON compatible dictionary."""
        logger.debug("Collecting story view setting for '%s'", self._name)
        if len(self._kind) == 2:
            return {
                "name": self._name,
                "uuid": self._uuid,
                "order": self._order,
                "kind": self._kind[1].rstrip("."),
                "settings": self._settings.copy(),
            }
        return {}

    def unpack(self, data: dict) -> None:
        """Unpack a dictionary and populate the class."""
        settings = data.get("settings", {})

        self.setName(data.get("name", ""))
        self.setOrder(data.get("order", 0))
        self.setKind(data.get("kind", 0))

        self._settings = {k: v[1] for k, v in SETTINGS_TEMPLATE.items()}
        if isinstance(settings, dict):
            for key, value in settings.items():
                if isinstance(key, str) and key.startswith(self._kind) and isinstance(value, T_BuildValue):
                    self.setValue(key, value)

        self._changed = False


class StoryViewCollection:
    """Manuscript: Story View Collection Class.

    This object holds all the story view setting objects defined by the
    given project. The story view settings are saved as a single JSON
    file in the project folder.
    """

    def __init__(self, project: NWProject) -> None:
        self._project = project
        self._views: dict[str, StoryViewSettings] = {}
        self._loadCollection()

    def __len__(self) -> int:
        """Return the number of story views."""
        return len(self._views)

    ##
    #  Getters
    ##

    def getStoryView(self, viewID: str) -> StoryViewSettings | None:
        """Get a specific story views settings object."""
        return self._views.get(viewID, None)

    ##
    #  Setters
    ##

    def setStoryView(self, view: StoryViewSettings) -> None:
        """Set story views settings data in the collection."""
        if isinstance(view, StoryViewSettings):
            self._views[view.viewID] = view
            self._saveCollection()

    ##
    #  Internal Functions
    ##

    def _loadCollection(self) -> bool:
        """Load build collections file."""
        buildsFile = self._project.storage.getMetaFile(nwFiles.VIEWS_FILE)
        if not isinstance(buildsFile, Path):
            return False

        data = {}
        if safeExists(buildsFile):
            logger.debug("Loading story views file")
            try:
                with open(buildsFile, mode="r", encoding="utf-8") as inFile:
                    data = json.load(inFile)
            except Exception:
                logger.error("Failed to load builds file")
                logException()
                return False

        if not isinstance(data, dict):
            logger.error("Story views file is not a JSON object")
            return False

        builds = data.get("novelWriter.storyViews", None)
        if not isinstance(builds, dict):
            logger.error("No novelWriter.storyViews in the story views file")
            return False

        for key, entry in builds.items():
            if isinstance(entry, dict):
                self._views[key] = StoryViewSettings.fromDict(entry)

        return True

    def _saveCollection(self) -> bool:
        """Save build collections file."""
        buildsFile = self._project.storage.getMetaFile(nwFiles.BUILDS_FILE)
        if not isinstance(buildsFile, Path):
            return False

        logger.debug("Saving story views file")
        try:
            data: dict[str, str | dict] = {}
            data.update({k: b.pack() for k, b in self._views.items()})
            with open(buildsFile, mode="w+", encoding="utf-8") as outFile:
                outFile.write(jsonEncode({"novelWriter.storyViews": data}, nmax=4))
        except Exception:
            logger.error("Failed to save story views file")
            logException()
            return False

        return True
