"""
Annotation data models and undoable commands for every annotation type.

Data classes use ``dataclasses`` with a UUID ``id`` field.  For every
annotation kind there is an *Add* and *Remove* command so that all
mutations flow through the :class:`UndoStack`.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field, replace
from typing import Literal

from PySide6.QtCore import QObject, Signal

from core.undo_redo import Command

logger = logging.getLogger(__name__)


# ===================================================================
# Data models
# ===================================================================

def _new_id() -> str:
    """Generate a new unique annotation id."""
    return uuid.uuid4().hex


@dataclass
class TextBoxData:
    """A user-placed text box overlay."""
    page_index: int
    rect: tuple[float, float, float, float]  # x, y, w, h
    text: str = ""
    font_family: str = "Noto Sans Bengali"
    font_size: float = 14.0
    color: str = "#000000"
    bold: bool = False
    italic: bool = False
    opacity: float = 1.0
    id: str = field(default_factory=_new_id)


@dataclass
class HighlightData:
    """A highlight / underline / strikethrough annotation."""
    page_index: int
    rect: tuple[float, float, float, float]  # x, y, w, h
    color: str = "#FFFF00"
    opacity: float = 0.5
    annotation_type: Literal["highlight", "underline", "strikethrough"] = "highlight"
    id: str = field(default_factory=_new_id)


@dataclass
class ShapeData:
    """A geometric shape (rectangle, line, or arrow)."""
    page_index: int
    shape_type: Literal["rect", "line", "arrow"] = "rect"
    start_point: tuple[float, float] = (0.0, 0.0)
    end_point: tuple[float, float] = (100.0, 100.0)
    stroke_color: str = "#000000"
    fill_color: str | None = None
    stroke_width: float = 1.0
    id: str = field(default_factory=_new_id)


@dataclass
class FreehandData:
    """A freehand drawing stroke."""
    page_index: int
    points: list[tuple[float, float]] = field(default_factory=list)
    color: str = "#000000"
    width: float = 2.0
    id: str = field(default_factory=_new_id)


@dataclass
class ImageData:
    """An image overlay."""
    page_index: int
    rect: tuple[float, float, float, float]  # x, y, w, h
    image_path: str = ""
    opacity: float = 1.0
    id: str = field(default_factory=_new_id)


@dataclass
class RedactData:
    """A redaction rectangle with optional replacement text."""
    page_index: int
    rect: tuple[float, float, float, float]  # x, y, w, h
    replacement_text: str = ""
    font_family: str = "Noto Sans Bengali"
    font_size: float = 12.0
    color: str = "#000000"
    id: str = field(default_factory=_new_id)


# ===================================================================
# Annotation manager
# ===================================================================

class AnnotationManager(QObject):
    """Central store for all annotation data.

    Signals are emitted so the UI can react to changes without polling.
    """

    annotation_added = Signal(object)     # emits the data object
    annotation_removed = Signal(str)      # emits the annotation id
    annotation_modified = Signal(object)  # emits the *new* data object

    def __init__(self) -> None:
        super().__init__()
        self._text_boxes: dict[str, TextBoxData] = {}
        self._highlights: dict[str, HighlightData] = {}
        self._shapes: dict[str, ShapeData] = {}
        self._freehands: dict[str, FreehandData] = {}
        self._images: dict[str, ImageData] = {}

    # ----- text boxes -----

    def add_text_box(self, data: TextBoxData) -> None:
        """Register a text box annotation."""
        self._text_boxes[data.id] = data
        logger.debug("Added text box %s on page %d", data.id, data.page_index)
        self.annotation_added.emit(data)

    def remove_text_box(self, text_id: str) -> None:
        """Remove a text box annotation by its id."""
        if text_id in self._text_boxes:
            del self._text_boxes[text_id]
            logger.debug("Removed text box %s", text_id)
            self.annotation_removed.emit(text_id)

    def get_text_box(self, text_id: str) -> TextBoxData | None:
        """Retrieve a single text box by id."""
        return self._text_boxes.get(text_id)

    def modify_text_box(self, text_id: str, new_data: TextBoxData) -> None:
        """Replace the text box data for *text_id* with *new_data*."""
        if text_id in self._text_boxes:
            self._text_boxes[text_id] = new_data
            logger.debug("Modified text box %s", text_id)
            self.annotation_modified.emit(new_data)

    # ----- highlights -----

    def add_highlight(self, data: HighlightData) -> None:
        """Register a highlight annotation."""
        self._highlights[data.id] = data
        logger.debug("Added highlight %s on page %d", data.id, data.page_index)
        self.annotation_added.emit(data)

    def remove_highlight(self, highlight_id: str) -> None:
        """Remove a highlight annotation by its id."""
        if highlight_id in self._highlights:
            del self._highlights[highlight_id]
            logger.debug("Removed highlight %s", highlight_id)
            self.annotation_removed.emit(highlight_id)

    def get_highlight(self, highlight_id: str) -> HighlightData | None:
        """Retrieve a single highlight by id."""
        return self._highlights.get(highlight_id)

    # ----- shapes -----

    def add_shape(self, data: ShapeData) -> None:
        """Register a shape annotation."""
        self._shapes[data.id] = data
        logger.debug("Added shape %s on page %d", data.id, data.page_index)
        self.annotation_added.emit(data)

    def remove_shape(self, shape_id: str) -> None:
        """Remove a shape annotation by its id."""
        if shape_id in self._shapes:
            del self._shapes[shape_id]
            logger.debug("Removed shape %s", shape_id)
            self.annotation_removed.emit(shape_id)

    def get_shape(self, shape_id: str) -> ShapeData | None:
        """Retrieve a single shape by id."""
        return self._shapes.get(shape_id)

    # ----- freehands -----

    def add_freehand(self, data: FreehandData) -> None:
        """Register a freehand drawing annotation."""
        self._freehands[data.id] = data
        logger.debug("Added freehand %s on page %d", data.id, data.page_index)
        self.annotation_added.emit(data)

    def remove_freehand(self, freehand_id: str) -> None:
        """Remove a freehand annotation by its id."""
        if freehand_id in self._freehands:
            del self._freehands[freehand_id]
            logger.debug("Removed freehand %s", freehand_id)
            self.annotation_removed.emit(freehand_id)

    def get_freehand(self, freehand_id: str) -> FreehandData | None:
        """Retrieve a single freehand by id."""
        return self._freehands.get(freehand_id)

    # ----- images -----

    def add_image(self, data: ImageData) -> None:
        """Register an image overlay annotation."""
        self._images[data.id] = data
        logger.debug("Added image %s on page %d", data.id, data.page_index)
        self.annotation_added.emit(data)

    def remove_image(self, image_id: str) -> None:
        """Remove an image annotation by its id."""
        if image_id in self._images:
            del self._images[image_id]
            logger.debug("Removed image %s", image_id)
            self.annotation_removed.emit(image_id)

    def get_image(self, image_id: str) -> ImageData | None:
        """Retrieve a single image by id."""
        return self._images.get(image_id)

    # ----- queries -----

    def get_annotations_for_page(
        self, page_index: int
    ) -> dict[str, list]:
        """Return all annotations on a given page, grouped by kind.

        Returns a dict with keys ``"text_boxes"``, ``"highlights"``,
        ``"shapes"``, ``"freehands"``, ``"images"``.
        """
        return {
            "text_boxes": [
                d for d in self._text_boxes.values() if d.page_index == page_index
            ],
            "highlights": [
                d for d in self._highlights.values() if d.page_index == page_index
            ],
            "shapes": [
                d for d in self._shapes.values() if d.page_index == page_index
            ],
            "freehands": [
                d for d in self._freehands.values() if d.page_index == page_index
            ],
            "images": [
                d for d in self._images.values() if d.page_index == page_index
            ],
        }

    def clear(self) -> None:
        """Remove every annotation from the manager."""
        self._text_boxes.clear()
        self._highlights.clear()
        self._shapes.clear()
        self._freehands.clear()
        self._images.clear()
        logger.debug("All annotations cleared.")


# ===================================================================
# Command subclasses – text boxes
# ===================================================================

class AddTextBoxCommand(Command):
    """Undoable: add a text box to the annotation manager."""

    def __init__(self, annotations_mgr: AnnotationManager, data: TextBoxData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.add_text_box(self._data)

    def undo(self) -> None:
        self._mgr.remove_text_box(self._data.id)

    @property
    def description(self) -> str:
        return f"Add text box on page {self._data.page_index}"


class RemoveTextBoxCommand(Command):
    """Undoable: remove a text box from the annotation manager."""

    def __init__(self, annotations_mgr: AnnotationManager, data: TextBoxData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.remove_text_box(self._data.id)

    def undo(self) -> None:
        self._mgr.add_text_box(self._data)

    @property
    def description(self) -> str:
        return f"Remove text box on page {self._data.page_index}"


class ModifyTextBoxCommand(Command):
    """Undoable: modify an existing text box's data."""

    def __init__(
        self,
        annotations_mgr: AnnotationManager,
        text_id: str,
        old_data: TextBoxData,
        new_data: TextBoxData,
    ) -> None:
        self._mgr = annotations_mgr
        self._text_id = text_id
        self._old_data = old_data
        self._new_data = new_data

    def execute(self) -> None:
        self._mgr.modify_text_box(self._text_id, self._new_data)

    def undo(self) -> None:
        self._mgr.modify_text_box(self._text_id, self._old_data)

    @property
    def description(self) -> str:
        return f"Modify text box {self._text_id}"


# ===================================================================
# Command subclasses – highlights
# ===================================================================

class AddHighlightCommand(Command):
    """Undoable: add a highlight annotation."""

    def __init__(self, annotations_mgr: AnnotationManager, data: HighlightData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.add_highlight(self._data)

    def undo(self) -> None:
        self._mgr.remove_highlight(self._data.id)

    @property
    def description(self) -> str:
        return f"Add {self._data.annotation_type} on page {self._data.page_index}"


class RemoveHighlightCommand(Command):
    """Undoable: remove a highlight annotation."""

    def __init__(self, annotations_mgr: AnnotationManager, data: HighlightData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.remove_highlight(self._data.id)

    def undo(self) -> None:
        self._mgr.add_highlight(self._data)

    @property
    def description(self) -> str:
        return f"Remove {self._data.annotation_type} on page {self._data.page_index}"


# ===================================================================
# Command subclasses – shapes
# ===================================================================

class AddShapeCommand(Command):
    """Undoable: add a shape annotation."""

    def __init__(self, annotations_mgr: AnnotationManager, data: ShapeData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.add_shape(self._data)

    def undo(self) -> None:
        self._mgr.remove_shape(self._data.id)

    @property
    def description(self) -> str:
        return f"Add {self._data.shape_type} on page {self._data.page_index}"


class RemoveShapeCommand(Command):
    """Undoable: remove a shape annotation."""

    def __init__(self, annotations_mgr: AnnotationManager, data: ShapeData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.remove_shape(self._data.id)

    def undo(self) -> None:
        self._mgr.add_shape(self._data)

    @property
    def description(self) -> str:
        return f"Remove {self._data.shape_type} on page {self._data.page_index}"


# ===================================================================
# Command subclasses – freehands
# ===================================================================

class AddFreehandCommand(Command):
    """Undoable: add a freehand drawing."""

    def __init__(self, annotations_mgr: AnnotationManager, data: FreehandData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.add_freehand(self._data)

    def undo(self) -> None:
        self._mgr.remove_freehand(self._data.id)

    @property
    def description(self) -> str:
        return f"Add freehand on page {self._data.page_index}"


class RemoveFreehandCommand(Command):
    """Undoable: remove a freehand drawing."""

    def __init__(self, annotations_mgr: AnnotationManager, data: FreehandData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.remove_freehand(self._data.id)

    def undo(self) -> None:
        self._mgr.add_freehand(self._data)

    @property
    def description(self) -> str:
        return f"Remove freehand on page {self._data.page_index}"


# ===================================================================
# Command subclasses – images
# ===================================================================

class AddImageCommand(Command):
    """Undoable: add an image overlay."""

    def __init__(self, annotations_mgr: AnnotationManager, data: ImageData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.add_image(self._data)

    def undo(self) -> None:
        self._mgr.remove_image(self._data.id)

    @property
    def description(self) -> str:
        return f"Add image on page {self._data.page_index}"


class RemoveImageCommand(Command):
    """Undoable: remove an image overlay."""

    def __init__(self, annotations_mgr: AnnotationManager, data: ImageData) -> None:
        self._mgr = annotations_mgr
        self._data = data

    def execute(self) -> None:
        self._mgr.remove_image(self._data.id)

    def undo(self) -> None:
        self._mgr.add_image(self._data)

    @property
    def description(self) -> str:
        return f"Remove image on page {self._data.page_index}"
