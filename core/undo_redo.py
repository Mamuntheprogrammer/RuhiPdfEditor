"""
Command-pattern undo/redo system.

Provides the abstract ``Command`` base class and a managed ``UndoStack``
that supports bounded history, redo, and Qt signals for UI updates.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract command
# ---------------------------------------------------------------------------

class Command(ABC):
    """Base class for all undoable commands.

    Subclasses must implement :meth:`execute` and :meth:`undo`.
    An optional human-readable :attr:`description` can be overridden
    for display in an undo history panel.
    """

    @abstractmethod
    def execute(self) -> None:
        """Perform the action represented by this command."""
        ...

    @abstractmethod
    def undo(self) -> None:
        """Reverse the action performed by :meth:`execute`."""
        ...

    @property
    def description(self) -> str:
        """Human-readable label for this command (defaults to class name)."""
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# Undo stack
# ---------------------------------------------------------------------------

class UndoStack(QObject):
    """Manages undo/redo history with signals for UI updates.

    Parameters
    ----------
    max_size:
        Maximum number of commands kept in the undo history.
        When exceeded the oldest command is silently discarded.
    """

    changed = Signal()  # Emitted whenever the stacks change

    def __init__(self, max_size: int = 100) -> None:
        super().__init__()
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._max_size = max_size

    # ----- public API -----

    def push(self, cmd: Command) -> None:
        """Execute *cmd* and push it onto the undo stack.

        The redo stack is cleared because a new action invalidates the
        previously undone future.
        """
        logger.debug("Executing command: %s", cmd.description)
        cmd.execute()
        self._undo_stack.append(cmd)
        # Enforce maximum history size
        if len(self._undo_stack) > self._max_size:
            discarded = self._undo_stack.pop(0)
            logger.debug("Discarded oldest command: %s", discarded.description)
        self._redo_stack.clear()
        self.changed.emit()

    def undo(self) -> None:
        """Undo the last command and move it to the redo stack."""
        if not self._undo_stack:
            logger.debug("Nothing to undo.")
            return
        cmd = self._undo_stack.pop()
        logger.debug("Undoing command: %s", cmd.description)
        cmd.undo()
        self._redo_stack.append(cmd)
        self.changed.emit()

    def redo(self) -> None:
        """Redo the last undone command and move it back to the undo stack."""
        if not self._redo_stack:
            logger.debug("Nothing to redo.")
            return
        cmd = self._redo_stack.pop()
        logger.debug("Redoing command: %s", cmd.description)
        cmd.execute()
        self._undo_stack.append(cmd)
        self.changed.emit()

    @property
    def can_undo(self) -> bool:
        """Return *True* if there is at least one command to undo."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Return *True* if there is at least one command to redo."""
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str | None:
        """Description of the command that would be undone, or *None*."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None

    @property
    def redo_description(self) -> str | None:
        """Description of the command that would be redone, or *None*."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None

    def clear(self) -> None:
        """Discard all undo and redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Undo stack cleared.")
        self.changed.emit()
