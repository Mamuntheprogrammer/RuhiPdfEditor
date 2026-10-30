"""
PDF Viewing and Editing Canvas.

Uses QGraphicsView and QGraphicsScene to display pages vertically,
manage overlay annotations (text boxes, shapes, drawings, highlights, images),
and handle interactive editing tools with full Bangla support and razor-sharp
anti-aliased vector rendering at any zoom level.
"""

from __future__ import annotations

import logging
import math
import unicodedata
import uuid
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, QRect, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFocusEvent,
    QFont,
    QFontMetrics,
    QImage,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsProxyWidget,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QTextEdit,
)

from core.annotations import (
    FreehandData,
    HighlightData,
    ImageData,
    RedactCommand,
    RedactData,
    ShapeData,
    TextBoxData,
)
from core.pdf_engine import TextBlock
from ui.dialogs import MultiLineTextDialog
from ui.toolbar import Tool

if TYPE_CHECKING:
    from core.bangla_input import BanglaPhoneticEngine
    from core.pdf_engine import PdfEngine
    from ui.i18n import I18n

logger = logging.getLogger(__name__)


# ====================================================================== #
#  Canvas Overlay Items
# ====================================================================== #

class PdfPageItem(QGraphicsItem):
    """Visual representation of a single rendered PDF page in the scene.

    Maintains vector-crisp high-DPI rendering so zooming never looks pixelated.
    Coordinates inside the scene are always 1:1 in PDF points.
    """

    def __init__(self, page_index: int, pt_width: float, pt_height: float, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.pt_width = pt_width
        self.pt_height = pt_height
        self._pixmap: Optional[QPixmap] = None
        self._rendered_zoom: float = 1.0

        # In scene, 1 unit = 1 PDF point
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.setZValue(0.0)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.pt_width + 8, self.pt_height + 8)

    def set_rendered_pixmap(self, pixmap: QPixmap, rendered_zoom: float = 1.0) -> None:
        self._pixmap = pixmap
        self._rendered_zoom = rendered_zoom
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        page_rect = QRectF(0, 0, self.pt_width, self.pt_height)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Drop shadow for clean modern paper elevation
        shadow_rect = page_rect.translated(3, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.drawRoundedRect(shadow_rect, 2, 2)

        # White page background with subtle border
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawRect(page_rect)

        # Draw the high-resolution vector rendered pixmap with floating point mapping
        if self._pixmap is not None and not self._pixmap.isNull():
            painter.drawPixmap(page_rect, self._pixmap, QRectF(self._pixmap.rect()))

        painter.restore()


class InlineCanvasTextEditor(QLineEdit):
    """Inline canvas text editor for in-place English editing and creation."""

    committed = Signal(str)
    cancelled = Signal()

    def __init__(self, initial_text: str = "", point_size: float = 12.0, parent=None):
        super().__init__(initial_text, parent)
        self.point_size = point_size
        self.setProperty("no_bangla_filter", True)
        self._handled = False
        fm = self.fontMetrics()
        self.setFixedWidth(max(60, fm.horizontalAdvance(initial_text) + 24))
        self.textChanged.connect(self._adjust_width)

    def _adjust_width(self, text: str) -> None:
        fm = self.fontMetrics()
        w = max(60, fm.horizontalAdvance(text) + 24)
        self.setFixedWidth(w)

    def commit(self) -> None:
        if not self._handled:
            self._handled = True
            self.committed.emit(self.text())

    def cancel(self) -> None:
        if not self._handled:
            self._handled = True
            self.cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.commit()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.cancel()
            event.accept()
            return
        # Backspace, Delete, and all typing keys are handled natively by QLineEdit
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self.commit()


class PdfTextBlockSelectionItem(QGraphicsObject):
    """Interactive selection box around an existing PDF text block.

    Allows one-click deletion, double-click editing/replacement, and Delete key erasing.
    """

    delete_requested = Signal(int, object)  # page_idx, TextBlock
    edit_requested = Signal(int, object)    # page_idx, TextBlock

    def __init__(self, page_idx: int, block: TextBlock, page_item: PdfPageItem, parent=None):
        super().__init__(parent)
        self.page_idx = page_idx
        self.block = block
        self.page_item = page_item
        x0, y0, x1, y1 = block.rect
        self.setPos(page_item.pos() + QPointF(x0, y0))
        self.rect_w = max(40.0, float(x1 - x0))
        self.rect_h = max(18.0, float(y1 - y0))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setZValue(15.0)

    def boundingRect(self) -> QRectF:
        return QRectF(-2, -2, self.rect_w + 22, self.rect_h + 4)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Selection outline with minimal opacity and no background fill for alignment visibility
        box = QRectF(0, 0, self.rect_w, self.rect_h)
        painter.setPen(QPen(QColor(2, 132, 199, 85), 1.0, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, 2, 2)

        # Delete '✕' button in red - subtle badge
        btn_s = 13.0
        btn_rect = QRectF(self.rect_w + 3, 1, btn_s, btn_s)
        painter.setBrush(QBrush(QColor(239, 68, 68, 140)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(btn_rect, 2, 2)
        painter.setPen(QPen(Qt.GlobalColor.white, 1.2))
        p = 3.5
        painter.drawLine(
            QPointF(btn_rect.left() + p, btn_rect.top() + p),
            QPointF(btn_rect.right() - p, btn_rect.bottom() - p),
        )
        painter.drawLine(
            QPointF(btn_rect.left() + p, btn_rect.bottom() - p),
            QPointF(btn_rect.right() - p, btn_rect.top() + p),
        )
        painter.restore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            btn_s = 14.0
            btn_rect = QRectF(self.rect_w + 3, 1, btn_s, btn_s)
            if btn_rect.contains(event.pos()):
                self.delete_requested.emit(self.page_idx, self.block)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.edit_requested.emit(self.page_idx, self.block)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit(self.page_idx, self.block)
            event.accept()
            return
        super().keyPressEvent(event)


class TextBoxItem(QGraphicsObject):
    """Interactive text box with full Qt/HarfBuzz Bangla shaping, repositioning, and live properties."""

    modified = Signal(object)          # emits TextBoxData
    deleted = Signal(object)           # emits TextBoxData
    edit_requested = Signal(object)     # emits TextBoxItem
    selected_changed = Signal(object)   # emits TextBoxData

    def __init__(
        self,
        data: TextBoxData,
        scale: float = 1.0,
        page_item: Optional[PdfPageItem] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.data = data
        self.scale_factor = scale
        self.page_item = page_item
        self._is_hovered = False

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(10.0)

    def boundingRect(self) -> QRectF:
        """Dynamically compute bounding rect based on actual rendered text size and scale."""
        font = QFont(self.data.font_family)
        target_size = max(1.0, float(self.data.font_size) * self.scale_factor)
        font.setPointSizeF(target_size)
        font.setBold(self.data.bold)
        font.setItalic(self.data.italic)
        font.setUnderline(getattr(self.data, "underline", False))
        font.setStrikeOut(getattr(self.data, "strikethrough", False))
        fm = QFontMetrics(font)
        text = self.data.text if self.data.text else " "
        br = fm.boundingRect(
            QRect(0, 0, 10000, 10000),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            text,
        )
        pad_x = 4.0
        pad_y = 2.0
        is_active = self.isSelected() or self._is_hovered
        extra_w = 18.0 if is_active else 4.0
        w = max(12.0, float(br.width()) + pad_x * 2.0 + extra_w)
        h = max(8.0, float(br.height()) + pad_y * 2.0)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        rect = self.boundingRect()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        is_active = self.isSelected() or self._is_hovered

        if is_active:
            # Minimal opacity border with NO background fill so user can see alignment clearly
            painter.setPen(QPen(QColor(2, 132, 199, 75), 1.0, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 2, 2)

            # Subtle baseline alignment guide line for pixel-perfect positioning
            font_t = QFont(self.data.font_family)
            font_t.setPointSizeF(max(1.0, float(self.data.font_size) * self.scale_factor))
            fm_t = QFontMetrics(font_t)
            baseline_y = 2.0 + float(fm_t.ascent())
            painter.setPen(QPen(QColor(2, 132, 199, 45), 0.75, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(4.0, baseline_y), QPointF(rect.width() - 20.0, baseline_y))

            # Corner handles - subtle small 3px notches
            painter.setBrush(QBrush(QColor(2, 132, 199, 110)))
            painter.setPen(Qt.PenStyle.NoPen)
            hs = 3.0
            painter.drawRect(QRectF(0, 0, hs, hs))
            painter.drawRect(QRectF(rect.width() - hs, 0, hs, hs))
            painter.drawRect(QRectF(0, rect.height() - hs, hs, hs))
            painter.drawRect(QRectF(rect.width() - hs, rect.height() - hs, hs, hs))

            # Red '✕' delete button in top-right corner - minimal subtle badge
            close_size = 13.0
            close_rect = QRectF(rect.width() - close_size - 2, 2, close_size, close_size)
            painter.setBrush(QBrush(QColor(239, 68, 68, 140)))
            painter.drawRoundedRect(close_rect, 2, 2)
            painter.setPen(QPen(Qt.GlobalColor.white, 1.2))
            pad = 3.5
            painter.drawLine(
                QPointF(close_rect.left() + pad, close_rect.top() + pad),
                QPointF(close_rect.right() - pad, close_rect.bottom() - pad),
            )
            painter.drawLine(
                QPointF(close_rect.left() + pad, close_rect.bottom() - pad),
                QPointF(close_rect.right() - pad, close_rect.top() + pad),
            )
        else:
            # Idle state on canvas: very faint minimal border so user can clearly see text alignment
            painter.setPen(QPen(QColor(2, 132, 199, 35), 0.75, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 2, 2)

            # Tiny subtle edit dot in bottom-right corner
            painter.setBrush(QBrush(QColor(2, 132, 199, 70)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(rect.width() - 3.5, rect.height() - 3.5), 1.5, 1.5)

        # Draw Bangla / Unicode text using HarfBuzz
        font = QFont(self.data.font_family)
        target_size = max(1.0, float(self.data.font_size) * self.scale_factor)
        font.setPointSizeF(target_size)
        font.setBold(self.data.bold)
        font.setItalic(self.data.italic)
        font.setUnderline(getattr(self.data, "underline", False))
        font.setStrikeOut(getattr(self.data, "strikethrough", False))
        painter.setFont(font)

        col = QColor(self.data.color)
        col.setAlphaF(self.data.opacity)
        painter.setPen(col)

        pad_x = 4.0
        pad_y = 2.0
        right_sub = 18.0 if is_active else 4.0
        text_rect = rect.adjusted(pad_x, pad_y, -right_sub, -pad_y)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            self.data.text,
        )
        painter.restore()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            self._sync_position()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.selected_changed.emit(self.data)
        return super().itemChange(change, value)

    def _sync_position(self) -> None:
        """Update internal data.rect with exact new position in PDF points."""
        if self.page_item is not None:
            scene_pos = self.pos()
            local_pos = scene_pos - self.page_item.pos()
            pt_x = local_pos.x()
            pt_y = local_pos.y()
            br = self.boundingRect()
            self.data.rect = (pt_x, pt_y, pt_x + br.width(), pt_y + br.height())
            self.modified.emit(self.data)

    def hoverEnterEvent(self, event) -> None:
        self._is_hovered = True
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._is_hovered = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            rect = self.boundingRect()
            close_size = 14.0
            close_rect = QRectF(rect.width() - close_size - 2, 2, close_size, close_size)
            if close_rect.contains(event.pos()):
                # User clicked the '✕' delete button!
                self.deleted.emit(self.data)
                event.accept()
                return
        super().mousePressEvent(event)
        self.setSelected(True)
        self.selected_changed.emit(self.data)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double click to edit text."""
        self.edit_requested.emit(self)
        event.accept()

    def contextMenuEvent(self, event) -> None:
        """Right click menu on text box."""
        menu = QMenu()
        act_edit = menu.addAction("✏️ Edit Text...")
        act_edit.triggered.connect(lambda: self.edit_requested.emit(self))
        act_del = menu.addAction("🗑️ Delete Text Box")
        act_del.triggered.connect(lambda: self.deleted.emit(self.data))
        menu.exec(event.screenPos())
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Backspace/Delete to remove, and Arrow keys for pixel-perfect positioning."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleted.emit(self.data)
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10.0 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1.0
            dx = -step if event.key() == Qt.Key.Key_Left else (step if event.key() == Qt.Key.Key_Right else 0.0)
            dy = -step if event.key() == Qt.Key.Key_Up else (step if event.key() == Qt.Key.Key_Down else 0.0)
            self.setPos(self.pos() + QPointF(dx, dy))
            self._sync_position()
            self.update()
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.edit_requested.emit(self)
            event.accept()
            return
        super().keyPressEvent(event)


class HighlightItem(QGraphicsRectItem):
    """Semi-transparent highlight, underline, or strikethrough overlay."""

    def __init__(self, data: HighlightData, scale: float = 1.0, parent=None):
        x0, y0, x1, y1 = data.rect
        w = max(10.0, abs(x1 - x0))
        h = max(4.0, abs(y1 - y0))
        rect = QRectF(0, 0, w * scale, h * scale)
        super().__init__(rect, parent)
        self.data = data
        self.setZValue(2.0)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

        color = QColor(data.color)
        color.setAlphaF(data.opacity)

        if data.annotation_type == "highlight":
            self.setPen(Qt.PenStyle.NoPen)
            self.setBrush(QBrush(color))
        elif data.annotation_type == "underline":
            self.setPen(QPen(color, 2.0))
            self.setBrush(Qt.BrushStyle.NoBrush)
        elif data.annotation_type == "strikethrough":
            self.setPen(QPen(color, 2.0))
            self.setBrush(Qt.BrushStyle.NoBrush)


class ShapeItem(QGraphicsItem):
    """Vector rectangle, line, or arrow overlay."""

    def __init__(self, data: ShapeData, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.data = data
        self.scale_factor = scale
        self.setZValue(5.0)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

    def boundingRect(self) -> QRectF:
        sx, sy = self.data.start_point
        ex, ey = self.data.end_point
        s = self.scale_factor
        x = min(sx, ex) * s
        y = min(sy, ey) * s
        w = abs(ex - sx) * s
        h = abs(ey - sy) * s
        pad = max(10.0, self.data.stroke_width * s * 2.0)
        return QRectF(x - pad, y - pad, w + pad * 2, h + pad * 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pen = QPen(QColor(self.data.stroke_color), self.data.stroke_width * self.scale_factor)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if self.data.fill_color:
            painter.setBrush(QBrush(QColor(self.data.fill_color)))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        s = self.scale_factor
        p1 = QPointF(self.data.start_point[0] * s, self.data.start_point[1] * s)
        p2 = QPointF(self.data.end_point[0] * s, self.data.end_point[1] * s)

        if self.data.shape_type == "rect":
            rx = min(p1.x(), p2.x())
            ry = min(p1.y(), p2.y())
            rw = abs(p2.x() - p1.x())
            rh = abs(p2.y() - p1.y())
            painter.drawRect(QRectF(rx, ry, rw, rh))

        elif self.data.shape_type == "line":
            painter.drawLine(p1, p2)

        elif self.data.shape_type == "arrow":
            painter.drawLine(p1, p2)
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            length = math.hypot(dx, dy)
            if length > 0.001:
                ux, uy = dx / length, dy / length
                vx, vy = -uy, ux
                arr_len = 12.0 * s
                arr_w = 6.0 * s
                b = QPointF(p2.x() - arr_len * ux, p2.y() - arr_len * uy)
                left = QPointF(b.x() + arr_w * vx, b.y() + arr_w * vy)
                right = QPointF(b.x() - arr_w * vx, b.y() - arr_w * vy)

                path = QPainterPath()
                path.moveTo(p2)
                path.lineTo(left)
                path.lineTo(right)
                path.closeSubpath()
                painter.setBrush(QBrush(QColor(self.data.stroke_color)))
                painter.drawPath(path)

        if self.isSelected():
            painter.setPen(QPen(QColor("#0284c7"), 1.0, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())

        painter.restore()


class FreehandItem(QGraphicsPathItem):
    """Freehand pen drawing overlay."""

    def __init__(self, data: FreehandData, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.data = data
        self.setZValue(6.0)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

        pen = QPen(QColor(data.color), data.width * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

        path = QPainterPath()
        if data.points:
            p0 = data.points[0]
            path.moveTo(p0[0] * scale, p0[1] * scale)
            for pt in data.points[1:]:
                path.lineTo(pt[0] * scale, pt[1] * scale)
        self.setPath(path)


class ImageItem(QGraphicsObject):
    """Inserted image or digital signature overlay with interactive resize handles and repositioning."""

    modified = Signal(object)
    deleted = Signal(object)
    selected_changed = Signal(object)

    def __init__(
        self,
        data: ImageData,
        scale: float = 1.0,
        page_item: Optional[PdfPageItem] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.data = data
        self.scale_factor = scale
        self.page_item = page_item
        self._pixmap = QPixmap(data.image_path)
        self._is_hovered = False
        self._close_hovered = False
        self._drag_handle: Optional[str] = None
        self._drag_start_scene_pos: Optional[QPointF] = None
        self._drag_start_rect: Optional[tuple[float, float, float, float]] = None

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(4.0)

    def _get_dims(self) -> tuple[float, float]:
        """Return (width_px, height_px) in scene coordinates."""
        w_pts = abs(self.data.rect[2] - self.data.rect[0])
        h_pts = abs(self.data.rect[3] - self.data.rect[1])
        w = max(15.0, w_pts * self.scale_factor)
        h = max(15.0, h_pts * self.scale_factor)
        return w, h

    def boundingRect(self) -> QRectF:
        w, h = self._get_dims()
        pad_top = 32.0
        pad_sides = 20.0
        pad_bottom = 14.0
        return QRectF(-pad_sides, -pad_top, w + pad_sides * 2.0, h + pad_top + pad_bottom)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        w, h = self._get_dims()
        img_rect = QRectF(0, 0, w, h)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setOpacity(self.data.opacity)

        if not self._pixmap.isNull():
            painter.drawPixmap(img_rect, self._pixmap, QRectF(self._pixmap.rect()))
        else:
            painter.setPen(QPen(QColor(148, 163, 184), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(241, 245, 249)))
            painter.drawRect(img_rect)

        is_active = self.isSelected() or self._is_hovered
        if is_active:
            # Selection dash border
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(2, 132, 199, 180), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(img_rect)

            # 4 corner resize handles
            hs = 7.0
            painter.setPen(QPen(QColor("#0284c7"), 1.5))
            painter.setBrush(QBrush(Qt.GlobalColor.white))
            for hx, hy in [(0, 0), (w, 0), (0, h), (w, h)]:
                painter.drawRect(QRectF(hx - hs / 2.0, hy - hs / 2.0, hs, hs))

            # Red circular '✕' delete badge outside top-right corner
            close_size = 20.0
            close_rect = QRectF(w - 6.0, -25.0, close_size, close_size)
            bg_color = QColor(220, 38, 38) if getattr(self, "_close_hovered", False) else QColor(239, 68, 68)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
            painter.drawEllipse(close_rect)
            painter.setPen(QPen(Qt.GlobalColor.white, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            pad = 5.5
            painter.drawLine(
                QPointF(close_rect.left() + pad, close_rect.top() + pad),
                QPointF(close_rect.right() - pad, close_rect.bottom() - pad),
            )
            painter.drawLine(
                QPointF(close_rect.left() + pad, close_rect.bottom() - pad),
                QPointF(close_rect.right() - pad, close_rect.top() + pad),
            )

        painter.restore()

    def _hit_close(self, pt: QPointF) -> bool:
        w, _ = self._get_dims()
        # close_rect is at (w - 6.0, -25.0, 20.0, 20.0)
        # Hit target ends at y = -1.0 so it never overlaps the image content or (w, 0) resize handle
        return QRectF(w - 10.0, -29.0, 28.0, 28.0).contains(pt)

    def _hit_handle(self, pt: QPointF) -> Optional[str]:
        if self._hit_close(pt):
            return None
        w, h = self._get_dims()
        hs = 10.0
        if QRectF(-hs, -hs, hs * 2, hs * 2).contains(pt):
            return "tl"
        if QRectF(w - hs, -hs, hs * 2, hs * 2).contains(pt):
            return "tr"
        if QRectF(-hs, h - hs, hs * 2, hs * 2).contains(pt):
            return "bl"
        if QRectF(w - hs, h - hs, hs * 2, hs * 2).contains(pt):
            return "br"
        return None

    def hoverEnterEvent(self, event) -> None:
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._is_hovered = False
        self._close_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def hoverMoveEvent(self, event) -> None:
        if self.isSelected() or self._is_hovered:
            pos = event.pos()
            hit_close = self._hit_close(pos)
            if hit_close != getattr(self, "_close_hovered", False):
                self._close_hovered = hit_close
                self.update()
            if hit_close:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                handle = self._hit_handle(pos)
                if handle in ("tl", "br"):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif handle in ("tr", "bl"):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif self.isSelected():
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    @staticmethod
    def _get_event_scene_pos(event) -> QPointF:
        if hasattr(event, "scenePos"):
            return event.scenePos()
        if hasattr(event, "scenePosition"):
            return event.scenePosition()
        if hasattr(event, "pos"):
            return QPointF(event.pos())
        return QPointF()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            if self._hit_close(pos):
                if self.scene():
                    self.scene().removeItem(self)
                self.deleted.emit(self.data)
                event.accept()
                return
            handle = self._hit_handle(pos)
            if handle is not None:
                self._drag_handle = handle
                self._drag_start_scene_pos = self._get_event_scene_pos(event)
                self._drag_start_rect = self.data.rect
                event.accept()
                return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.scene():
                self.scene().removeItem(self)
            self.deleted.emit(self.data)
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10.0 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1.0
            dx = -step if event.key() == Qt.Key.Key_Left else (step if event.key() == Qt.Key.Key_Right else 0.0)
            dy = -step if event.key() == Qt.Key.Key_Up else (step if event.key() == Qt.Key.Key_Down else 0.0)
            self.setPos(self.pos() + QPointF(dx, dy))
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()
        act_del = menu.addAction("🗑 Delete Image")
        act_del.triggered.connect(self._delete_self)
        menu.exec(event.screenPos())
        event.accept()

    def _delete_self(self) -> None:
        if self.scene():
            self.scene().removeItem(self)
        self.deleted.emit(self.data)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_handle is not None
            and self._drag_start_scene_pos is not None
            and self._drag_start_rect is not None
        ):
            delta = self._get_event_scene_pos(event) - self._drag_start_scene_pos
            dx = delta.x() / self.scale_factor
            dy = delta.y() / self.scale_factor
            x0, y0, x1, y1 = self._drag_start_rect
            min_dim = 15.0

            if self._drag_handle == "br":
                new_x1 = max(x0 + min_dim, x1 + dx)
                new_y1 = max(y0 + min_dim, y1 + dy)
                self.data.rect = (x0, y0, new_x1, new_y1)
            elif self._drag_handle == "bl":
                new_x0 = min(x1 - min_dim, x0 + dx)
                new_y1 = max(y0 + min_dim, y1 + dy)
                self.data.rect = (new_x0, y0, x1, new_y1)
                if self.page_item:
                    self.setPos(
                        self.page_item.pos()
                        + QPointF(new_x0 * self.scale_factor, y0 * self.scale_factor)
                    )
            elif self._drag_handle == "tr":
                new_x1 = max(x0 + min_dim, x1 + dx)
                new_y0 = min(y1 - min_dim, y0 + dy)
                self.data.rect = (x0, new_y0, new_x1, y1)
                if self.page_item:
                    self.setPos(
                        self.page_item.pos()
                        + QPointF(x0 * self.scale_factor, new_y0 * self.scale_factor)
                    )
            elif self._drag_handle == "tl":
                new_x0 = min(x1 - min_dim, x0 + dx)
                new_y0 = min(y1 - min_dim, y0 + dy)
                self.data.rect = (new_x0, new_y0, x1, y1)
                if self.page_item:
                    self.setPos(
                        self.page_item.pos()
                        + QPointF(new_x0 * self.scale_factor, new_y0 * self.scale_factor)
                    )

            self.prepareGeometryChange()
            self.update()
            self.modified.emit(self.data)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_handle is not None:
            self._drag_handle = None
            self._drag_start_scene_pos = None
            self._drag_start_rect = None
            self.modified.emit(self.data)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.scene():
            if self.page_item is not None and self._drag_handle is None:
                local_pos = self.pos() - self.page_item.pos()
                pt_x = local_pos.x() / self.scale_factor
                pt_y = local_pos.y() / self.scale_factor
                w = abs(self.data.rect[2] - self.data.rect[0])
                h = abs(self.data.rect[3] - self.data.rect[1])
                self.data.rect = (pt_x, pt_y, pt_x + w, pt_y + h)
                self.modified.emit(self.data)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.selected_changed.emit(self.data)
            self.update()
        return super().itemChange(change, value)


# ====================================================================== #
#  PdfView (Main Graphics View)
# ====================================================================== #

class PdfView(QGraphicsView):
    """Main viewer and editor canvas for PDF documents."""

    page_changed = Signal(int)
    zoom_changed = Signal(float)
    text_box_added = Signal(TextBoxData)
    text_box_selected = Signal(object)  # emits TextBoxData when selected
    shape_selected = Signal(object)     # emits ShapeData when selected
    annotation_selected = Signal(object) # emits HighlightData when selected
    image_selected = Signal(object)      # emits ImageData when selected
    selection_cleared = Signal()
    annotation_added = Signal(object)
    annotation_deleted = Signal(str)
    tool_switched = Signal(Tool)
    document_modified = Signal()

    PAGE_SPACING = 25  # Vertical gap between pages in scene

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._engine: Optional[PdfEngine] = None
        self._bangla_engine: Optional[BanglaPhoneticEngine] = None
        self._i18n: Optional[I18n] = None

        self._current_tool = Tool.SELECT
        self._current_page_index = 0
        self._zoom = 1.0
        self._fit_mode = "width"

        self._page_items: list[PdfPageItem] = []
        self._overlay_items: dict[str, QGraphicsItem] = {}
        self._current_text_selection: Optional[PdfTextBlockSelectionItem] = None

        # Interaction / drawing state
        self._is_mouse_down = False
        self._draw_start_pt = QPointF()
        self._current_draw_item: Optional[QGraphicsItem] = None
        self._freehand_points: list[tuple[float, float]] = []

        # Current style properties cache
        self.current_properties: dict = {
            "font_family": "Noto Sans Bengali",
            "font_size": 14.0,
            "color": "#000000",
            "bold": False,
            "italic": False,
            "stroke_color": "#0284c7",
            "fill_color": "",
            "stroke_width": 2.0,
            "opacity": 0.85,
        }

        self._init_view_settings()
        self._scene.selectionChanged.connect(self._on_scene_selection_changed)

    def _init_view_settings(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.setBackgroundBrush(Qt.BrushStyle.NoBrush)

    def set_dependencies(self, engine: PdfEngine, bangla: BanglaPhoneticEngine, i18n: I18n) -> None:
        self._engine = engine
        self._bangla_engine = bangla
        self._i18n = i18n

    def set_tool(self, tool: Tool) -> None:
        self._clear_live_preview()
        self._is_mouse_down = False
        self._current_tool = tool
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        if tool == Tool.SELECT:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        elif tool == Tool.TEXT:
            self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        elif tool == Tool.ERASER:
            self.setCursor(QCursor(Qt.CursorShape.ForbiddenCursor))
        elif tool in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKETHROUGH):
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif tool in (Tool.RECTANGLE, Tool.LINE, Tool.ARROW):
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif tool == Tool.FREEHAND:
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        elif tool in (Tool.IMAGE, Tool.SIGNATURE):
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def update_properties(self, props: dict) -> None:
        """Update property cache and apply immediately to any selected items."""
        self.current_properties.update(props)

        # Apply to any currently selected items
        selected = self._scene.selectedItems()
        for it in selected:
            if isinstance(it, TextBoxItem):
                if "font_family" in props and props["font_family"]:
                    it.data.font_family = props["font_family"]
                if "font_size" in props and props["font_size"]:
                    it.data.font_size = float(props["font_size"])
                if "color" in props and props["color"]:
                    it.data.color = props["color"]
                if "bold" in props:
                    it.data.bold = bool(props["bold"])
                if "italic" in props:
                    it.data.italic = bool(props["italic"])
                if "underline" in props:
                    it.data.underline = bool(props["underline"])
                if "strikethrough" in props:
                    it.data.strikethrough = bool(props["strikethrough"])
                if "opacity" in props and props["opacity"] is not None:
                    it.data.opacity = float(props["opacity"])
                it.prepareGeometryChange()
                it._sync_position()
                it.update()
                if self._engine:
                    self._engine.annotation_manager.modify_text_box(it.data.id, it.data)
                self.document_modified.emit()
            elif isinstance(it, HighlightItem):
                if "color" in props and props["color"]:
                    it.data.color = props["color"]
                if "opacity" in props and props["opacity"] is not None:
                    it.data.opacity = float(props["opacity"])
                if "annotation_type" in props and props["annotation_type"]:
                    it.data.annotation_type = props["annotation_type"]
                col = QColor(it.data.color)
                col.setAlphaF(it.data.opacity)
                if it.data.annotation_type == "highlight":
                    it.setPen(Qt.PenStyle.NoPen)
                    it.setBrush(QBrush(col))
                else:
                    it.setPen(QPen(col, 2.0))
                    it.setBrush(Qt.BrushStyle.NoBrush)
                it.update()
                if self._engine:
                    self._engine.annotation_manager.modify_highlight(it.data.id, it.data)
                self.document_modified.emit()
            elif isinstance(it, ShapeItem):
                if "stroke_color" in props and props["stroke_color"]:
                    it.data.stroke_color = props["stroke_color"]
                if "fill_color" in props:
                    it.data.fill_color = props["fill_color"]
                if "stroke_width" in props and props["stroke_width"]:
                    it.data.stroke_width = float(props["stroke_width"])
                it.update()
                if self._engine:
                    self._engine.annotation_manager.modify_shape(it.data.id, it.data)
                self.document_modified.emit()
            elif isinstance(it, ImageItem):
                if "opacity" in props and props["opacity"] is not None:
                    it.data.opacity = float(props["opacity"])
                    it.update()
                    if self._engine:
                        self._engine.annotation_manager.modify_image(it.data.id, it.data)
                    self.document_modified.emit()

    def _on_scene_selection_changed(self) -> None:
        """Notify properties panel when selection changes."""
        selected = self._scene.selectedItems()
        if len(selected) == 1:
            it = selected[0]
            if isinstance(it, TextBoxItem):
                self.text_box_selected.emit(it.data)
            elif isinstance(it, ShapeItem):
                self.shape_selected.emit(it.data)
            elif isinstance(it, HighlightItem):
                self.annotation_selected.emit(it.data)
            elif isinstance(it, ImageItem):
                self.image_selected.emit(it.data)
        elif not selected and self._current_tool == Tool.SELECT:
            self.selection_cleared.emit()

    # ================================================================== #
    #  Document Loading & Rendering (Vector Sharpness Guaranteed)
    # ================================================================== #

    def load_document(self, engine: PdfEngine, preserve_view: bool = False) -> None:
        self._engine = engine
        self._scene.clear()
        self._page_items.clear()
        self._overlay_items.clear()
        self._current_text_selection = None

        if not engine or engine.page_count == 0:
            return

        saved_zoom = self._zoom if preserve_view else None

        # Supersampled high-DPI rendering so vector text and graphics are razor sharp
        render_scale = max(2.5, (saved_zoom or 1.0) * 2.5)

        # Calculate max page width to center all pages horizontally along canvas
        max_pt_w = max(engine.get_page_size(i)[0] for i in range(engine.page_count))
        scene_w = max_pt_w + 2 * self.PAGE_SPACING
        y_offset = self.PAGE_SPACING

        for i in range(engine.page_count):
            pt_w, pt_h = engine.get_page_size(i)
            page_item = PdfPageItem(i, pt_w, pt_h)
            page_x = (scene_w - pt_w) / 2.0
            page_item.setPos(page_x, y_offset)

            pixmap = engine.render_page(i, zoom=render_scale)
            page_item.set_rendered_pixmap(pixmap, render_scale)

            self._scene.addItem(page_item)
            self._page_items.append(page_item)
            y_offset += pt_h + self.PAGE_SPACING

        self._scene.setSceneRect(0, 0, scene_w, y_offset)

        # Re-attach any existing annotations from manager
        mgr = engine.annotation_manager
        for tb in mgr.text_boxes:
            if 0 <= tb.page_index < len(self._page_items):
                self._add_text_box_item(tb, self._page_items[tb.page_index])
        for hl in mgr.highlights:
            if 0 <= hl.page_index < len(self._page_items):
                self._add_highlight_item(hl, self._page_items[hl.page_index])
        for sh in mgr.shapes:
            if 0 <= sh.page_index < len(self._page_items):
                self._add_shape_item(sh, self._page_items[sh.page_index])
        for fh in mgr.freehands:
            if 0 <= fh.page_index < len(self._page_items):
                self._add_freehand_item(fh, self._page_items[fh.page_index])
        for img in mgr.images:
            if 0 <= img.page_index < len(self._page_items):
                self._add_image_item(img, self._page_items[img.page_index])

        self.page_changed.emit(self._current_page_index if preserve_view else 0)

        # Default zoom mode is fit to width on open
        if preserve_view and saved_zoom is not None:
            self.set_zoom(saved_zoom)
        else:
            self._fit_mode = "width"
            self.zoom_fit_width()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(30, self.zoom_fit_width)
            QTimer.singleShot(100, self.zoom_fit_width)

    def refresh_page(self, page_index: int) -> None:
        if not self._engine or page_index >= len(self._page_items):
            return
        page_item = self._page_items[page_index]
        render_scale = max(2.5, self._zoom * 2.5)
        new_pixmap = self._engine.render_page(page_index, zoom=render_scale)
        page_item.set_rendered_pixmap(new_pixmap, render_scale)

    # ================================================================== #
    #  Zoom & Navigation (Vector Scaling without pixelation)
    # ================================================================== #

    def set_zoom(self, zoom: float) -> None:
        zoom = max(0.2, min(5.0, zoom))
        self._zoom = zoom
        self.resetTransform()
        self.scale(self._zoom, self._zoom)
        self.zoom_changed.emit(self._zoom)

        # Dynamic high-resolution re-rendering: always re-render with supersampling
        render_scale = max(2.5, self._zoom * 2.5)
        if self._engine and self._engine.is_open:
            for page_item in self._page_items:
                pixmap = self._engine.render_page(page_item.page_index, zoom=render_scale)
                page_item.set_rendered_pixmap(pixmap, render_scale)

    def zoom_in(self) -> None:
        self._fit_mode = "manual"
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        self._fit_mode = "manual"
        self.set_zoom(self._zoom / 1.25)

    def zoom_actual_size(self) -> None:
        """Actual size: 100% (1:1 PDF point scale)."""
        self._fit_mode = "manual"
        self.set_zoom(1.0)

    def zoom_fit_width(self) -> None:
        """Fit page width to viewport width."""
        if not self._page_items:
            return
        cur_idx = max(0, min(self._current_page_index, len(self._page_items) - 1))
        pt_w = self._page_items[cur_idx].pt_width
        if pt_w <= 0:
            return
        scrollbar_w = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 18
        avail_w = self.viewport().width() - scrollbar_w - 24
        if avail_w > 50:
            target_zoom = max(0.2, min(5.0, avail_w / pt_w))
            self._fit_mode = "width"
            self.set_zoom(target_zoom)
            page_item = self._page_items[cur_idx]
            self.centerOn(page_item.pos().x() + pt_w / 2.0, page_item.pos().y())
        else:
            self._fit_mode = "width"
            self.set_zoom(1.0)

    def zoom_fit_height(self) -> None:
        """Fit page height to viewport height."""
        self._fit_mode = "height"
        if not self._page_items:
            return
        cur_idx = max(0, min(self._current_page_index, len(self._page_items) - 1))
        pt_h = self._page_items[cur_idx].pt_height
        view_h = self.viewport().height() - 40
        if pt_h > 0 and view_h > 50:
            target_zoom = max(0.2, min(5.0, view_h / pt_h))
            self.set_zoom(target_zoom)
            self.centerOn(self._page_items[cur_idx])

    def zoom_fit_page(self) -> None:
        """Zoom to page level: fit entire page inside viewport."""
        self._fit_mode = "page"
        if not self._page_items:
            return
        cur_idx = max(0, min(self._current_page_index, len(self._page_items) - 1))
        pt_w = self._page_items[cur_idx].pt_width
        pt_h = self._page_items[cur_idx].pt_height
        view_w = self.viewport().width() - 40
        view_h = self.viewport().height() - 40
        if pt_w > 0 and pt_h > 0 and view_w > 50 and view_h > 50:
            target_zoom = max(0.2, min(5.0, min(view_w / pt_w, view_h / pt_h)))
            self.set_zoom(target_zoom)
            self.centerOn(self._page_items[cur_idx])

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if getattr(self, "_fit_mode", "width") == "width" and self._page_items:
            cur_idx = max(0, min(self._current_page_index, len(self._page_items) - 1))
            pt_w = self._page_items[cur_idx].pt_width
            scrollbar_w = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 18
            avail_w = self.viewport().width() - scrollbar_w - 24
            if pt_w > 0 and avail_w > 50:
                target_zoom = max(0.2, min(5.0, avail_w / pt_w))
                if abs(self._zoom - target_zoom) > 0.01:
                    self.set_zoom(target_zoom)

    def go_to_page(self, page_index: int) -> None:
        if 0 <= page_index < len(self._page_items):
            page_item = self._page_items[page_index]
            self.centerOn(page_item)
            self._current_page_index = page_index
            self.page_changed.emit(page_index)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self._update_current_page_from_viewport()

    def _update_current_page_from_viewport(self) -> None:
        """Detect which page is currently most visible in the viewport and update active page."""
        if not self._page_items:
            return

        vp = self.viewport()
        if vp.height() <= 0:
            return

        scene_rect = self.mapToScene(vp.rect()).boundingRect()
        max_overlap = -1.0
        best_page = self._current_page_index

        for page_item in self._page_items:
            top_y = page_item.pos().y()
            bot_y = top_y + page_item.pt_height
            overlap = max(0.0, min(scene_rect.bottom(), bot_y) - max(scene_rect.top(), top_y))
            if overlap > max_overlap:
                max_overlap = overlap
                best_page = page_item.page_index

        if best_page != self._current_page_index and max_overlap > 0:
            self._current_page_index = best_page
            self.page_changed.emit(best_page)

    def get_viewport_center_on_page(self, page_index: int) -> tuple[float, float]:
        """Return (x, y) coordinates on the given page corresponding to current viewport view."""
        if not (0 <= page_index < len(self._page_items)):
            return 100.0, 100.0
        page_item = self._page_items[page_index]
        vp = self.viewport()
        vp_center = vp.rect().center()
        scene_center = self.mapToScene(vp_center)
        local_pt = scene_center - page_item.pos()
        # Clamp nicely so the 150x150 image and its top-floating delete badge stay comfortably within page boundaries
        x = max(20.0, min(max(20.0, page_item.pt_width - 170.0), local_pt.x() - 75.0))
        y = max(35.0, min(max(35.0, page_item.pt_height - 170.0), local_pt.y() - 75.0))
        return x, y

    # ================================================================== #
    #  Coordinate Utilities
    # ================================================================== #

    def _get_page_under_pos(self, scene_pos: QPointF) -> Optional[tuple[int, PdfPageItem, QPointF]]:
        """Return (page_index, page_item, local_pt_pos) for a scene position."""
        for page_item in self._page_items:
            local = scene_pos - page_item.pos()
            if 0 <= local.x() <= page_item.pt_width and 0 <= local.y() <= page_item.pt_height:
                return page_item.page_index, page_item, local
        return None

    def _find_text_block_at(self, page_idx: int, local_pt: QPointF, tolerance: float = 8.0) -> Optional[TextBlock]:
        """Find the text block / word closest to local_pt within tolerance points."""
        if not self._engine:
            return None
        text_blocks = self._engine.get_text_blocks(page_idx, level="word")
        px = local_pt.x()
        py = local_pt.y()

        best_block = None
        min_dist = float("inf")

        for tb in text_blocks:
            x0, y0, x1, y1 = tb.rect
            if (x0 - tolerance) <= px <= (x1 + tolerance) and (y0 - tolerance) <= py <= (y1 + tolerance):
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                dist = (px - cx) ** 2 + (py - cy) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_block = tb

        return best_block

    # ================================================================== #
    #  Deletion / Erasing Helpers
    # ================================================================== #

    def delete_selected(self) -> None:
        """Delete all currently selected overlay items or selected text blocks."""
        selected = self._scene.selectedItems()
        for it in selected:
            # Check if this is an existing PDF text block selection
            if isinstance(it, PdfTextBlockSelectionItem):
                self._erase_text_block(it.page_idx, it.block)
                if it.scene():
                    self._scene.removeItem(it)
                self._current_text_selection = None
                continue

            ann_id = getattr(it, "data", None)
            if ann_id and hasattr(ann_id, "id"):
                self.annotation_deleted.emit(ann_id.id)
                if ann_id.id in self._overlay_items:
                    del self._overlay_items[ann_id.id]
            if it.scene():
                self._scene.removeItem(it)
        if selected:
            self.document_modified.emit()

    def _on_item_deleted(self, item_id: str, item: QGraphicsItem) -> None:
        """Remove item triggered from internal handle."""
        self.annotation_deleted.emit(item_id)
        if item_id in self._overlay_items:
            del self._overlay_items[item_id]
        if item.scene():
            self._scene.removeItem(item)
        self.document_modified.emit()

    def _on_item_modified(self, data) -> None:
        if self._engine:
            self._engine.annotation_manager.modify_text_box(data.id, data)
        self.document_modified.emit()

    def _erase_text_block(self, page_idx: int, block: TextBlock) -> None:
        """Erase / redact existing word from the PDF."""
        if self._engine:
            parent_win = self.window()
            if hasattr(parent_win, "_undo_stack"):
                cmd = RedactCommand(self._engine, page_idx, block.rect, replacement_text="")
                parent_win._undo_stack.push(cmd)
            else:
                self._engine.redact_area(page_idx, block.rect, replacement_text="")
            self.refresh_page(page_idx)
            if self._current_text_selection and self._current_text_selection.scene():
                self._scene.removeItem(self._current_text_selection)
                self._current_text_selection = None
            self.document_modified.emit()

    def _clear_text_block_selection(self) -> None:
        """Clear active text block selection item if any."""
        if self._current_text_selection is not None:
            if self._current_text_selection.scene():
                self._scene.removeItem(self._current_text_selection)
            self._current_text_selection = None

    def _select_text_block(self, page_idx: int, block: TextBlock, page_item: PdfPageItem) -> None:
        """Select an existing single word from the PDF and show an interactive box."""
        self._clear_text_block_selection()
        self._scene.clearSelection()

        item = PdfTextBlockSelectionItem(page_idx, block, page_item)
        item.delete_requested.connect(self._erase_text_block)
        item.edit_requested.connect(self._redact_and_replace_block)
        self._scene.addItem(item)
        item.setSelected(True)
        self._current_text_selection = item

        # Populate properties panel with auto-detected font features
        is_bangla = any(0x0980 <= ord(c) <= 0x09FF for c in block.text)
        if is_bangla:
            font_fam = "Noto Sans Bengali"
        elif block.font_name:
            font_fam = block.font_name
        else:
            font_fam = "Noto Sans"

        detected_sz = float(block.font_size) if block.font_size and block.font_size > 0 else 12.0
        detected_col = block.color if block.color else "#000000"

        tb_data = TextBoxData(
            page_index=page_idx,
            rect=block.rect,
            text=block.text,
            font_family=font_fam,
            font_size=detected_sz,
            color=detected_col,
            bold=block.bold,
            italic=block.italic,
        )
        self.current_properties["font_family"] = font_fam
        self.current_properties["font_size"] = detected_sz
        self.current_properties["color"] = detected_col
        self.current_properties["bold"] = block.bold
        self.current_properties["italic"] = block.italic
        self.text_box_selected.emit(tb_data)

    # ================================================================== #
    #  Mouse Events & Tool Interactions
    # ================================================================== #

    def _clear_live_preview(self) -> None:
        """Remove temporary drag preview shape or highlight from scene."""
        if hasattr(self, "_live_preview_item") and self._live_preview_item is not None:
            if self._live_preview_item.scene():
                self._scene.removeItem(self._live_preview_item)
            self._live_preview_item = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._clear_live_preview()
            scene_pos = self.mapToScene(event.pos())
            target = self._get_page_under_pos(scene_pos)

            if target is not None:
                page_idx, page_item, local_pt = target
                if page_idx != self._current_page_index:
                    self._current_page_index = page_idx
                    self.page_changed.emit(page_idx)

                # 1. Text Tool -> Check if existing text box or PDF word was clicked, otherwise create new
                if self._current_tool == Tool.TEXT:
                    item = self.itemAt(event.pos())
                    if isinstance(item, TextBoxItem):
                        self._scene.clearSelection()
                        item.setSelected(True)
                        self.text_box_selected.emit(item.data)
                        self._edit_text_box(item)
                        return
                    hit_block = self._find_text_block_at(page_idx, local_pt, tolerance=6.0)
                    if hit_block:
                        self._redact_and_replace_block(page_idx, hit_block)
                        return
                    self._create_inline_text_dialog(page_idx, page_item, local_pt)
                    return

                # 2. Select Tool -> Detect clicked single word or pass through
                elif self._current_tool == Tool.SELECT:
                    item = self.itemAt(event.pos())
                    if item is None or item == page_item:
                        hit_block = self._find_text_block_at(page_idx, local_pt, tolerance=6.0)
                        if hit_block:
                            self._select_text_block(page_idx, hit_block, page_item)
                            return
                        self._clear_text_block_selection()

                # 3. Eraser Tool -> Erase clicked single word or clicked overlay item
                elif self._current_tool == Tool.ERASER:
                    item = self.itemAt(event.pos())
                    if item and item != page_item and hasattr(item, "data"):
                        ann_id = getattr(item.data, "id", None)
                        if ann_id:
                            self._on_item_deleted(ann_id, item)
                            return

                    # Check clicked single word from PDF
                    hit_block = self._find_text_block_at(page_idx, local_pt, tolerance=6.0)
                    if hit_block:
                        self._erase_text_block(page_idx, hit_block)
                        return

                    self._is_mouse_down = True
                    self._draw_start_pt = local_pt
                    return

                # 4. Freehand Pen -> Start path
                elif self._current_tool == Tool.FREEHAND:
                    self._is_mouse_down = True
                    self._freehand_points = [(local_pt.x(), local_pt.y())]
                    return

                # 5. Shape or Highlight -> Start drag
                elif self._current_tool in (
                    Tool.RECTANGLE, Tool.LINE, Tool.ARROW,
                    Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKETHROUGH,
                ):
                    self._is_mouse_down = True
                    self._draw_start_pt = local_pt
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_mouse_down:
            scene_pos = self.mapToScene(event.pos())
            target = self._get_page_under_pos(scene_pos)
            if target is not None:
                page_idx, page_item, local_pt = target
                scale = page_item.scale_x
                page_x = page_item.pos().x()
                page_y = page_item.pos().y()

                # 1. Freehand Pen (live smooth path)
                if self._current_tool == Tool.FREEHAND:
                    self._freehand_points.append((local_pt.x(), local_pt.y()))
                    if len(self._freehand_points) > 1:
                        path = QPainterPath()
                        p0 = self._freehand_points[0]
                        path.moveTo(page_x + p0[0] * scale, page_y + p0[1] * scale)
                        for pt in self._freehand_points[1:]:
                            path.lineTo(page_x + pt[0] * scale, page_y + pt[1] * scale)
                        if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsPathItem):
                            self._clear_live_preview()
                            self._live_preview_item = QGraphicsPathItem()
                            self._live_preview_item.setZValue(100.0)
                            self._scene.addItem(self._live_preview_item)
                        pen = QPen(
                            QColor(self.current_properties.get("stroke_color", "#000000")),
                            self.current_properties.get("stroke_width", 2.0) * scale,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin,
                        )
                        self._live_preview_item.setPen(pen)
                        self._live_preview_item.setPath(path)

                # 2. Highlight (Rectangle WITHOUT border, live highlight color and opacity)
                elif self._current_tool == Tool.HIGHLIGHT:
                    rx0 = min(self._draw_start_pt.x(), local_pt.x())
                    ry0 = min(self._draw_start_pt.y(), local_pt.y())
                    rw = abs(local_pt.x() - self._draw_start_pt.x())
                    rh = abs(local_pt.y() - self._draw_start_pt.y())
                    scene_rect = QRectF(page_x + rx0 * scale, page_y + ry0 * scale, rw * scale, rh * scale)

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsRectItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsRectItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    col = QColor(self.current_properties.get("color", "#ffeb3b"))
                    col.setAlphaF(self.current_properties.get("opacity", 0.45))
                    self._live_preview_item.setPen(Qt.PenStyle.NoPen)
                    self._live_preview_item.setBrush(QBrush(col))
                    self._live_preview_item.setRect(scene_rect)

                # 3. Underline / Strike live preview
                elif self._current_tool in (Tool.UNDERLINE, Tool.STRIKETHROUGH):
                    rx0 = min(self._draw_start_pt.x(), local_pt.x())
                    ry0 = min(self._draw_start_pt.y(), local_pt.y())
                    rw = abs(local_pt.x() - self._draw_start_pt.x())
                    rh = abs(local_pt.y() - self._draw_start_pt.y())
                    line_y = ry0 + rh if self._current_tool == Tool.UNDERLINE else ry0 + rh / 2.0
                    p1 = QPointF(page_x + rx0 * scale, page_y + line_y * scale)
                    p2 = QPointF(page_x + (rx0 + rw) * scale, page_y + line_y * scale)

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsLineItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsLineItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    col = QColor(self.current_properties.get("color", "#ef4444"))
                    col.setAlphaF(self.current_properties.get("opacity", 0.9))
                    pen = QPen(col, 2.0 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    self._live_preview_item.setPen(pen)
                    self._live_preview_item.setLine(p1.x(), p1.y(), p2.x(), p2.y())

                # 4. Rectangle (live vector rectangle with stroke and fill)
                elif self._current_tool == Tool.RECTANGLE:
                    rx0 = min(self._draw_start_pt.x(), local_pt.x())
                    ry0 = min(self._draw_start_pt.y(), local_pt.y())
                    rw = abs(local_pt.x() - self._draw_start_pt.x())
                    rh = abs(local_pt.y() - self._draw_start_pt.y())
                    scene_rect = QRectF(page_x + rx0 * scale, page_y + ry0 * scale, rw * scale, rh * scale)

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsRectItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsRectItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    stroke_col = QColor(self.current_properties.get("stroke_color", "#0284c7"))
                    stroke_w = self.current_properties.get("stroke_width", 2.0) * scale
                    self._live_preview_item.setPen(QPen(stroke_col, stroke_w))
                    fill = self.current_properties.get("fill_color", "")
                    if fill:
                        self._live_preview_item.setBrush(QBrush(QColor(fill)))
                    else:
                        self._live_preview_item.setBrush(Qt.BrushStyle.NoBrush)
                    self._live_preview_item.setRect(scene_rect)

                # 5. Line (live vector line)
                elif self._current_tool == Tool.LINE:
                    p1 = QPointF(page_x + self._draw_start_pt.x() * scale, page_y + self._draw_start_pt.y() * scale)
                    p2 = QPointF(page_x + local_pt.x() * scale, page_y + local_pt.y() * scale)

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsLineItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsLineItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    stroke_col = QColor(self.current_properties.get("stroke_color", "#0284c7"))
                    stroke_w = self.current_properties.get("stroke_width", 2.0) * scale
                    pen = QPen(stroke_col, stroke_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    self._live_preview_item.setPen(pen)
                    self._live_preview_item.setLine(p1.x(), p1.y(), p2.x(), p2.y())

                # 6. Arrow (live vector arrow with arrowhead)
                elif self._current_tool == Tool.ARROW:
                    p1 = QPointF(page_x + self._draw_start_pt.x() * scale, page_y + self._draw_start_pt.y() * scale)
                    p2 = QPointF(page_x + local_pt.x() * scale, page_y + local_pt.y() * scale)

                    path = QPainterPath()
                    path.moveTo(p1)
                    path.lineTo(p2)
                    dx = p2.x() - p1.x()
                    dy = p2.y() - p1.y()
                    length = math.hypot(dx, dy)
                    if length > 0.001:
                        ux, uy = dx / length, dy / length
                        vx, vy = -uy, ux
                        arr_len = 12.0 * scale
                        arr_w = 6.0 * scale
                        b = QPointF(p2.x() - arr_len * ux, p2.y() - arr_len * uy)
                        left = QPointF(b.x() + arr_w * vx, b.y() + arr_w * vy)
                        right = QPointF(b.x() - arr_w * vx, b.y() - arr_w * vy)
                        path.moveTo(left)
                        path.lineTo(p2)
                        path.lineTo(right)
                        path.closeSubpath()

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsPathItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsPathItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    stroke_col = QColor(self.current_properties.get("stroke_color", "#0284c7"))
                    stroke_w = self.current_properties.get("stroke_width", 2.0) * scale
                    pen = QPen(stroke_col, stroke_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                    self._live_preview_item.setPen(pen)
                    self._live_preview_item.setBrush(QBrush(stroke_col))
                    self._live_preview_item.setPath(path)

                # 7. Eraser area
                elif self._current_tool == Tool.ERASER:
                    rx0 = min(self._draw_start_pt.x(), local_pt.x())
                    ry0 = min(self._draw_start_pt.y(), local_pt.y())
                    rw = abs(local_pt.x() - self._draw_start_pt.x())
                    rh = abs(local_pt.y() - self._draw_start_pt.y())
                    scene_rect = QRectF(page_x + rx0 * scale, page_y + ry0 * scale, rw * scale, rh * scale)

                    if not isinstance(getattr(self, "_live_preview_item", None), QGraphicsRectItem):
                        self._clear_live_preview()
                        self._live_preview_item = QGraphicsRectItem()
                        self._live_preview_item.setZValue(100.0)
                        self._scene.addItem(self._live_preview_item)

                    self._live_preview_item.setPen(QPen(QColor(239, 68, 68), 1.0, Qt.PenStyle.DashLine))
                    self._live_preview_item.setBrush(QBrush(QColor(239, 68, 68, 40)))
                    self._live_preview_item.setRect(scene_rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._clear_live_preview()
        if event.button() == Qt.MouseButton.LeftButton and self._is_mouse_down:
            self._is_mouse_down = False
            scene_pos = self.mapToScene(event.pos())
            target = self._get_page_under_pos(scene_pos)

            if target is not None:
                page_idx, page_item, local_pt = target

                # Eraser area
                if self._current_tool == Tool.ERASER:
                    rx = min(self._draw_start_pt.x(), local_pt.x())
                    ry = min(self._draw_start_pt.y(), local_pt.y())
                    rw = abs(local_pt.x() - self._draw_start_pt.x())
                    rh = abs(local_pt.y() - self._draw_start_pt.y())
                    if rw > 4 and rh > 4 and self._engine:
                        self._engine.redact_area(page_idx, (rx, ry, rx + rw, ry + rh), replacement_text="")
                        self.refresh_page(page_idx)
                    return

                # Freehand
                elif self._current_tool == Tool.FREEHAND:
                    if len(self._freehand_points) > 1:
                        data = FreehandData(
                            id=str(uuid.uuid4()),
                            page_index=page_idx,
                            points=self._freehand_points.copy(),
                            color=self.current_properties.get("stroke_color", "#000000"),
                            width=self.current_properties.get("stroke_width", 2.0),
                        )
                        self._add_freehand_item(data, page_item)
                        self.annotation_added.emit(data)
                    self._freehand_points = []
                    return

                # Shapes
                elif self._current_tool in (Tool.RECTANGLE, Tool.LINE, Tool.ARROW):
                    shape_type_map = {
                        Tool.RECTANGLE: "rect",
                        Tool.LINE: "line",
                        Tool.ARROW: "arrow",
                    }
                    st = shape_type_map[self._current_tool]
                    data = ShapeData(
                        id=str(uuid.uuid4()),
                        page_index=page_idx,
                        shape_type=st,
                        start_point=(self._draw_start_pt.x(), self._draw_start_pt.y()),
                        end_point=(local_pt.x(), local_pt.y()),
                        stroke_color=self.current_properties.get("stroke_color", "#0284c7"),
                        fill_color=self.current_properties.get("fill_color", ""),
                        stroke_width=self.current_properties.get("stroke_width", 2.0),
                    )
                    self._add_shape_item(data, page_item)
                    self.annotation_added.emit(data)
                    return

                # Highlights
                elif self._current_tool in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKETHROUGH):
                    type_map = {
                        Tool.HIGHLIGHT: "highlight",
                        Tool.UNDERLINE: "underline",
                        Tool.STRIKETHROUGH: "strikethrough",
                    }
                    ann_t = type_map[self._current_tool]
                    rx0 = min(self._draw_start_pt.x(), local_pt.x())
                    ry0 = min(self._draw_start_pt.y(), local_pt.y())
                    rx1 = max(self._draw_start_pt.x(), local_pt.x())
                    ry1 = max(self._draw_start_pt.y(), local_pt.y())
                    rw = rx1 - rx0
                    rh = ry1 - ry0
                    if rw > 4 and rh > 4:
                        color = self.current_properties.get("color", "#ffeb3b" if ann_t == "highlight" else "#ef4444")
                        data = HighlightData(
                            id=str(uuid.uuid4()),
                            page_index=page_idx,
                            rect=(rx0, ry0, rx1, ry1),
                            color=color,
                            opacity=0.45 if ann_t == "highlight" else 0.9,
                            annotation_type=ann_t,
                        )
                        self._add_highlight_item(data, page_item)
                        self.annotation_added.emit(data)
                    return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double click to edit word or text box directly in the text edit window."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos_pt = event.position().toPoint() if hasattr(event, "position") else event.pos()

            # 1. Check all items directly under mouse cursor
            for item in self.items(pos_pt):
                if isinstance(item, TextBoxItem):
                    self._edit_text_box(item)
                    event.accept()
                    return
                if isinstance(item, PdfTextBlockSelectionItem):
                    self._redact_and_replace_block(item.page_idx, item.block)
                    event.accept()
                    return

            # 2. Check if current active word selection was double-clicked
            scene_pos = self.mapToScene(pos_pt)
            target = self._get_page_under_pos(scene_pos)
            if target is not None:
                page_idx, page_item, local_pt = target
                if self._current_text_selection is not None and self._current_text_selection.page_idx == page_idx:
                    bx0, by0, bx1, by1 = self._current_text_selection.block.rect
                    if (bx0 - 10.0) <= local_pt.x() <= (bx1 + 10.0) and (by0 - 10.0) <= local_pt.y() <= (by1 + 10.0):
                        self._redact_and_replace_block(page_idx, self._current_text_selection.block)
                        event.accept()
                        return

                # 3. Find closest word on page with comfortable 8.0 pt tolerance
                hit_block = self._find_text_block_at(page_idx, local_pt, tolerance=8.0)
                if hit_block is not None:
                    self._redact_and_replace_block(page_idx, hit_block)
                    event.accept()
                    return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Ctrl + Wheel zooms in/out."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Delete/Backspace key, Arrow keys for alignment positioning, and Undo/Redo."""
        # If an active inline text editor / proxy widget has focus, let it receive all keystrokes (like Backspace)
        focus_item = self._scene.focusItem() if self._scene else None
        if isinstance(focus_item, QGraphicsProxyWidget) or isinstance(
            QApplication.focusWidget(), (QLineEdit, QTextEdit, QPlainTextEdit)
        ):
            super().keyPressEvent(event)
            return

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10.0 if (event.modifiers() & Qt.KeyboardModifier.ShiftModifier) else 1.0
            dx = -step if event.key() == Qt.Key.Key_Left else (step if event.key() == Qt.Key.Key_Right else 0.0)
            dy = -step if event.key() == Qt.Key.Key_Up else (step if event.key() == Qt.Key.Key_Down else 0.0)
            selected = self._scene.selectedItems()
            moved = False
            for it in selected:
                if isinstance(it, TextBoxItem):
                    it.setPos(it.pos() + QPointF(dx, dy))
                    it._sync_position()
                    it.update()
                    moved = True
                elif isinstance(it, QGraphicsItem) and (it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable):
                    it.setPos(it.pos() + QPointF(dx, dy))
                    if hasattr(it, "_sync_position"):
                        it._sync_position()
                    it.update()
                    moved = True
            if moved:
                self.document_modified.emit()
                event.accept()
                return
        if event.matches(QKeySequence.StandardKey.Undo):
            parent_win = self.window()
            if hasattr(parent_win, "action_undo"):
                parent_win.action_undo()
                event.accept()
                return
        if event.matches(QKeySequence.StandardKey.Redo) or (
            event.key() == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            parent_win = self.window()
            if hasattr(parent_win, "action_redo"):
                parent_win.action_redo()
                event.accept()
                return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        """Right-click menu: Erase existing text, Redact & Replace, Add text, or Delete item."""
        scene_pos = self.mapToScene(event.pos())
        target = self._get_page_under_pos(scene_pos)

        menu = QMenu(self)
        if target is not None and self._engine:
            page_idx, page_item, local_pt = target

            # Check if there is an existing text word from the PDF under this point
            text_blocks = self._engine.get_text_blocks(page_idx, level="word")
            hit_block = None
            for tb in text_blocks:
                x0, y0, x1, y1 = tb.rect
                if (x0 - 2.0) <= local_pt.x() <= (x1 + 2.0) and (y0 - 2.0) <= local_pt.y() <= (y1 + 2.0):
                    hit_block = tb
                    break

            if hit_block:
                short_text = hit_block.text.strip().replace("\n", " ")[:20]
                act_erase = menu.addAction(f"🗑️ Delete Word: \"{short_text}\"")
                act_erase.triggered.connect(lambda: self._erase_text_block(page_idx, hit_block))

                redact_label = self._i18n.t("tool_redact") if self._i18n else "Replace Word"
                act_redact = menu.addAction(f"✏️ {redact_label} \"{short_text}\"...")
                act_redact.triggered.connect(lambda: self._redact_and_replace_block(page_idx, hit_block))
            else:
                act_redact_area = menu.addAction(self._i18n.t("tool_redact") if self._i18n else "Redact / White-out Area")
                act_redact_area.triggered.connect(lambda: self._redact_point_area(page_idx, local_pt))

            act_add_text = menu.addAction(self._i18n.t("tool_text") if self._i18n else "Add Text Here")
            act_add_text.triggered.connect(lambda: self._create_inline_text_dialog(page_idx, page_item, local_pt))

        if self._scene.selectedItems():
            menu.addSeparator()
            act_del = menu.addAction("🗑️ Delete Selected (Del)")
            act_del.triggered.connect(self.delete_selected)

        if not menu.isEmpty():
            menu.exec(event.globalPos())

    def _redact_and_replace_block(self, page_idx: int, block: TextBlock) -> None:
        is_bangla = any(0x0980 <= ord(c) <= 0x09FF for c in block.text)
        detected_sz = float(block.font_size) if block.font_size and block.font_size > 0 else 12.0
        detected_col = block.color if block.color else "#000000"
        detected_fam = block.font_name if (block.font_name and not is_bangla) else self.current_properties.get(
            "font_family", "Noto Sans Bengali" if is_bangla else "Noto Sans"
        )
        detected_bold = bool(block.bold)
        detected_italic = bool(block.italic)

        # Synchronize properties panel with auto-detected word font features
        self.current_properties["font_family"] = detected_fam
        self.current_properties["font_size"] = detected_sz
        self.current_properties["color"] = detected_col
        self.current_properties["bold"] = detected_bold
        self.current_properties["italic"] = detected_italic
        tb_data = TextBoxData(
            page_index=page_idx,
            rect=block.rect,
            text=block.text,
            font_family=detected_fam,
            font_size=detected_sz,
            color=detected_col,
            bold=detected_bold,
            italic=detected_italic,
        )
        self.text_box_selected.emit(tb_data)

        # Store scroll position so dialog opening/closing never shifts the viewport
        h_scroll = self.horizontalScrollBar().value()
        v_scroll = self.verticalScrollBar().value()

        # Normalize initial text with Unicode NFC
        clean_text = unicodedata.normalize("NFC", block.text)

        title = self._i18n.t("tool_redact") if self._i18n else "Redact & Replace"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text=clean_text,
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
            initial_bangla_mode=is_bangla,
        )
        try:
            if dlg.exec():
                final_text = dlg.get_text()
                if final_text is not None:
                    if not final_text.strip():
                        # Empty text: erase / delete the word
                        self._erase_text_block(page_idx, block)
                        return

                    final_text = unicodedata.normalize("NFC", final_text)
                    parent_win = self.window()

                    # If replacement text contains Bangla, use a Bangla font; otherwise use properties or detected font
                    is_replacement_bangla = any(0x0980 <= ord(c) <= 0x09FF for c in final_text)
                    if is_replacement_bangla:
                        font_fam = self.current_properties.get("font_family", "Noto Sans Bengali")
                        if font_fam not in ("Noto Sans Bengali", "SolaimanLipi", "Kalpurush", "Nikosh"):
                            font_fam = "Noto Sans Bengali"
                    else:
                        font_fam = self.current_properties.get("font_family") or detected_fam

                    # If user did not edit properties, these remain identical to the detected word's features.
                    # If user DID edit properties in the panel, their edits are applied!
                    font_sz = float(self.current_properties.get("font_size", detected_sz))
                    col = self.current_properties.get("color", detected_col)
                    is_bold = bool(self.current_properties.get("bold", detected_bold))
                    is_italic = bool(self.current_properties.get("italic", detected_italic))

                    if hasattr(parent_win, "_undo_stack"):
                        cmd = RedactCommand(
                            self._engine,
                            page_idx,
                            block.rect,
                            replacement_text=final_text,
                            font_family=font_fam,
                            font_size=font_sz,
                            color=col,
                            bold=is_bold,
                            italic=is_italic,
                        )
                        parent_win._undo_stack.push(cmd)
                    else:
                        self._engine.redact_area(
                            page_idx,
                            block.rect,
                            replacement_text=final_text,
                            font_family=font_fam,
                            font_size=font_sz,
                            color=col,
                            bold=is_bold,
                            italic=is_italic,
                        )
                    self.refresh_page(page_idx)
                    self.document_modified.emit()
        finally:
            self._clear_text_block_selection()
            self.horizontalScrollBar().setValue(h_scroll)
            self.verticalScrollBar().setValue(v_scroll)

    def _start_inline_editing_block(self, page_idx: int, block: TextBlock) -> None:
        """Start inline editing of an English text block directly on canvas with auto-detected font features."""
        if 0 <= page_idx < len(self._page_items):
            page_item = self._page_items[page_idx]
        else:
            return

        self._clear_text_block_selection()

        orig_font_fam = block.font_name or "Noto Sans"
        orig_font_sz = float(block.font_size if block.font_size and block.font_size > 0 else 12.0)
        orig_col = block.color or "#000000"
        orig_bold = block.bold
        orig_italic = block.italic

        # Synchronize properties panel with original detected font features
        self.current_properties["font_family"] = orig_font_fam
        self.current_properties["font_size"] = orig_font_sz
        self.current_properties["color"] = orig_col
        self.current_properties["bold"] = orig_bold
        self.current_properties["italic"] = orig_italic
        tb_data = TextBoxData(
            page_index=page_idx,
            rect=block.rect,
            text=block.text,
            font_family=orig_font_fam,
            font_size=orig_font_sz,
            color=orig_col,
            bold=orig_bold,
            italic=orig_italic,
        )
        self.text_box_selected.emit(tb_data)

        editor = InlineCanvasTextEditor(block.text, point_size=orig_font_sz)
        font = QFont(orig_font_fam)
        font.setPointSizeF(max(6.0, orig_font_sz))
        font.setBold(orig_bold)
        font.setItalic(orig_italic)
        editor.setFont(font)
        editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: #ffffff;
                color: {orig_col};
                border: 1px solid rgba(2, 132, 199, 0.7);
                border-radius: 2px;
                padding: 0px 2px;
            }}
        """)

        x0, y0, x1, y1 = block.rect
        w = max(float(x1 - x0) + 16.0, 50.0)
        h = max(float(y1 - y0) + 4.0, 18.0)
        editor.setFixedSize(int(w), int(h))

        proxy = self._scene.addWidget(editor)
        proxy.setPos(page_item.pos() + QPointF(x0 - 2, y0 - 2))
        proxy.setZValue(200.0)

        def on_commit(new_text: str):
            if proxy.scene():
                self._scene.removeItem(proxy)
            if new_text != block.text:
                if not new_text.strip():
                    # User cleared all text with backspace: erase/delete the word!
                    self._erase_text_block(page_idx, block)
                    return

                # Apply exact original font features for 100% consistency!
                active_fam = orig_font_fam
                active_sz = orig_font_sz
                active_col = orig_col
                active_bold = orig_bold
                active_italic = orig_italic

                parent_win = self.window()
                if hasattr(parent_win, "_undo_stack"):
                    cmd = RedactCommand(
                        self._engine,
                        page_idx,
                        block.rect,
                        replacement_text=new_text,
                        font_family=active_fam,
                        font_size=active_sz,
                        color=active_col,
                        bold=active_bold,
                        italic=active_italic,
                    )
                    parent_win._undo_stack.push(cmd)
                else:
                    self._engine.redact_area(
                        page_idx,
                        block.rect,
                        replacement_text=new_text,
                        font_family=active_fam,
                        font_size=active_sz,
                        color=active_col,
                        bold=active_bold,
                        italic=active_italic,
                    )
                self.refresh_page(page_idx)
                self.document_modified.emit()

        def on_cancel():
            if proxy.scene():
                self._scene.removeItem(proxy)

        editor.committed.connect(on_commit)
        editor.cancelled.connect(on_cancel)
        editor.setFocus()
        editor.selectAll()

    def _redact_point_area(self, page_idx: int, local_pt: QPointF) -> None:
        title = self._i18n.t("tool_redact") if self._i18n else "Redact & Replace"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text="",
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
        )
        if dlg.exec():
            final_text = dlg.get_text()
            if final_text is not None:
                rect = (local_pt.x(), local_pt.y(), local_pt.x() + 180.0, local_pt.y() + 30.0)
                parent_win = self.window()
                font_fam = self.current_properties.get("font_family", "Noto Sans Bengali")
                font_sz = float(self.current_properties.get("font_size", 14.0))
                col = self.current_properties.get("color", "#000000")
                if hasattr(parent_win, "_undo_stack"):
                    cmd = RedactCommand(
                        self._engine,
                        page_idx,
                        rect,
                        replacement_text=final_text,
                        font_family=font_fam,
                        font_size=font_sz,
                        color=col,
                    )
                    parent_win._undo_stack.push(cmd)
                else:
                    self._engine.redact_area(
                        page_idx,
                        rect,
                        replacement_text=final_text,
                        font_family=font_fam,
                        font_size=font_sz,
                        color=col,
                    )
                self.refresh_page(page_idx)
                self.document_modified.emit()

    # ================================================================== #
    #  Annotation Creation Helpers
    # ================================================================== #

    def _create_inline_text_dialog(self, page_idx: int, page_item: PdfPageItem, local_pt: QPointF) -> None:
        """Create new text: inline on canvas for English, or dialog for Bangla."""
        is_phonetic = bool(
            self._bangla_engine
            and (getattr(self._bangla_engine, "is_active", False) or getattr(self._bangla_engine, "avro_phonetic_enabled", False))
        )
        if not is_phonetic:
            self._start_inline_create_text(page_idx, page_item, local_pt)
            return

        h_scroll = self.horizontalScrollBar().value()
        v_scroll = self.verticalScrollBar().value()

        title = self._i18n.t("tool_text") if self._i18n else "Add Text"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text="",
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
            initial_bangla_mode=True,
        )
        try:
            if dlg.exec():
                final_text = dlg.get_text()
                if final_text and final_text.strip():
                    import unicodedata
                    final_text = unicodedata.normalize("NFC", final_text.strip())

                    is_bangla_text = any(0x0980 <= ord(c) <= 0x09FF for c in final_text)
                    font_fam = self.current_properties.get("font_family", "Noto Sans Bengali")
                    if is_bangla_text and font_fam not in ("Noto Sans Bengali", "SolaimanLipi", "Kalpurush", "Nikosh"):
                        font_fam = "Noto Sans Bengali"

                    font_sz = float(self.current_properties.get("font_size", 14.0))
                    is_bold = bool(self.current_properties.get("bold", False))
                    is_italic = bool(self.current_properties.get("italic", False))
                    col = self.current_properties.get("color", "#000000")

                    # Compute natural text dimensions
                    font = QFont(font_fam)
                    font.setPointSizeF(max(1.0, font_sz))
                    font.setBold(is_bold)
                    font.setItalic(is_italic)
                    fm = QFontMetrics(font)
                    br = fm.boundingRect(
                        QRect(0, 0, 10000, 10000),
                        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                        final_text,
                    )
                    init_w = max(24.0, float(br.width()) + 16.0)
                    init_h = max(16.0, float(br.height()) + 8.0)

                    data = TextBoxData(
                        id=str(uuid.uuid4()),
                        page_index=page_idx,
                        rect=(local_pt.x(), local_pt.y(), local_pt.x() + init_w, local_pt.y() + init_h),
                        text=final_text,
                        font_family=font_fam,
                        font_size=font_sz,
                        color=col,
                        bold=is_bold,
                        italic=is_italic,
                        opacity=1.0,
                    )
                    item = self._add_text_box_item(data, page_item)
                    self.text_box_added.emit(data)
                    self.document_modified.emit()

                    # Auto-select the newly added text box and switch back to SELECT tool
                    self._scene.clearSelection()
                    item.setSelected(True)
                    item.setFocus()
                    self.text_box_selected.emit(item.data)
                    self.set_tool(Tool.SELECT)
                    self.tool_switched.emit(Tool.SELECT)
        finally:
            self.horizontalScrollBar().setValue(h_scroll)
            self.verticalScrollBar().setValue(v_scroll)

    def _start_inline_create_text(self, page_idx: int, page_item: PdfPageItem, local_pt: QPointF) -> None:
        """Create new text box directly inline on canvas for English text."""
        font_fam = self.current_properties.get("font_family", "Noto Sans")
        font_sz = float(self.current_properties.get("font_size", 14.0))
        is_bold = bool(self.current_properties.get("bold", False))
        is_italic = bool(self.current_properties.get("italic", False))
        col = self.current_properties.get("color", "#000000")

        editor = InlineCanvasTextEditor("")
        editor.setProperty("no_bangla_filter", True)
        font = QFont(font_fam)
        font.setPointSizeF(max(6.0, font_sz))
        font.setBold(is_bold)
        font.setItalic(is_italic)
        editor.setFont(font)
        editor.setPlaceholderText("Type text...")
        editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: #ffffff;
                color: {col};
                border: 1px solid rgba(2, 132, 199, 0.7);
                border-radius: 2px;
                padding: 0px 4px;
            }}
        """)
        editor.setFixedSize(140, max(24, int(font_sz + 8)))

        proxy = self._scene.addWidget(editor)
        proxy.setPos(page_item.pos() + local_pt)
        proxy.setZValue(200.0)

        def on_commit(new_text: str):
            if proxy.scene():
                self._scene.removeItem(proxy)
            stripped = new_text.strip()
            if stripped:
                active_fam = self.current_properties.get("font_family", font_fam)
                active_sz = float(self.current_properties.get("font_size", font_sz))
                active_bold = bool(self.current_properties.get("bold", is_bold))
                active_italic = bool(self.current_properties.get("italic", is_italic))
                active_col = self.current_properties.get("color", col)

                font_c = QFont(active_fam)
                font_c.setPointSizeF(max(1.0, active_sz))
                font_c.setBold(active_bold)
                font_c.setItalic(active_italic)
                fm = QFontMetrics(font_c)
                br = fm.boundingRect(
                    QRect(0, 0, 10000, 10000),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                    stripped,
                )
                init_w = max(16.0, float(br.width()) + 16.0)
                init_h = max(8.0, float(br.height()) + 8.0)

                data = TextBoxData(
                    id=str(uuid.uuid4()),
                    page_index=page_idx,
                    rect=(local_pt.x(), local_pt.y(), local_pt.x() + init_w, local_pt.y() + init_h),
                    text=stripped,
                    font_family=active_fam,
                    font_size=active_sz,
                    color=active_col,
                    bold=active_bold,
                    italic=active_italic,
                    opacity=1.0,
                )
                item = self._add_text_box_item(data, page_item)
                self.text_box_added.emit(data)
                self.document_modified.emit()

                self._scene.clearSelection()
                item.setSelected(True)
                item.setFocus()
                self.text_box_selected.emit(item.data)
                self.set_tool(Tool.SELECT)
                self.tool_switched.emit(Tool.SELECT)

        def on_cancel():
            if proxy.scene():
                self._scene.removeItem(proxy)

        editor.committed.connect(on_commit)
        editor.cancelled.connect(on_cancel)
        editor.setFocus()

    def _edit_text_box(self, item: TextBoxItem) -> None:
        """Edit existing text box via multi-line text edit dialog."""
        self._scene.clearSelection()
        item.setSelected(True)
        self.text_box_selected.emit(item.data)

        h_scroll = self.horizontalScrollBar().value()
        v_scroll = self.verticalScrollBar().value()

        title = self._i18n.t("tool_text") if self._i18n else "Edit Text"
        is_bangla_tb = any(0x0980 <= ord(c) <= 0x09FF for c in item.data.text)
        use_bangla_mode = is_bangla_tb or bool(getattr(self._bangla_engine, "is_active", False))
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text=item.data.text,
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
            initial_bangla_mode=use_bangla_mode,
        )
        try:
            if dlg.exec():
                final_text = dlg.get_text()
                if final_text is not None and final_text != item.data.text:
                    if not final_text.strip():
                        self._on_item_deleted(item.data.id, item)
                        return
                    item.data.text = final_text
                    # If replacement has Bangla, ensure Bangla font family
                    if any(0x0980 <= ord(c) <= 0x09FF for c in final_text):
                        if item.data.font_family not in ("Noto Sans Bengali", "SolaimanLipi", "Kalpurush", "Nikosh"):
                            item.data.font_family = "Noto Sans Bengali"
                    item.prepareGeometryChange()
                    item._sync_position()
                    item.update()
                    if self._engine:
                        self._engine.annotation_manager.modify_text_box(item.data.id, item.data)
                    self.text_box_selected.emit(item.data)
                    self.document_modified.emit()
        finally:
            self.horizontalScrollBar().setValue(h_scroll)
            self.verticalScrollBar().setValue(v_scroll)

    def _start_inline_editing_textbox(self, item: TextBoxItem) -> None:
        """Inline editing for an existing TextBoxItem directly on canvas."""
        page_item = item.page_item
        if not page_item:
            return

        editor = InlineCanvasTextEditor(item.data.text)
        font = QFont(item.data.font_family)
        font.setPointSizeF(max(6.0, item.data.font_size))
        font.setBold(item.data.bold)
        font.setItalic(item.data.italic)
        editor.setFont(font)
        editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: #ffffff;
                color: {item.data.color};
                border: 1px solid rgba(2, 132, 199, 0.7);
                border-radius: 2px;
                padding: 0px 2px;
            }}
        """)
        br = item.boundingRect()
        editor.setFixedSize(max(int(br.width()), 50), max(int(br.height()), 18))

        proxy = self._scene.addWidget(editor)
        proxy.setPos(item.pos())
        proxy.setZValue(200.0)
        item.setVisible(False)

        def on_commit(new_text: str):
            if proxy.scene():
                self._scene.removeItem(proxy)
            item.setVisible(True)
            if new_text != item.data.text:
                if not new_text.strip():
                    # User cleared text with Backspace: delete text box!
                    self._on_item_deleted(item.data.id, item)
                    return
                item.data.text = new_text
                item.prepareGeometryChange()
                item._sync_position()
                item.update()
                if self._engine:
                    self._engine.annotation_manager.modify_text_box(item.data.id, item.data)
                self.text_box_selected.emit(item.data)
                self.document_modified.emit()

        def on_cancel():
            if proxy.scene():
                self._scene.removeItem(proxy)
            item.setVisible(True)

        editor.committed.connect(on_commit)
        editor.cancelled.connect(on_cancel)
        editor.setFocus()
        editor.selectAll()

    def _add_text_box_item(self, data: TextBoxData, page_item: PdfPageItem) -> TextBoxItem:
        scale = page_item.scale_x
        item = TextBoxItem(data, scale=scale, page_item=page_item)
        item.setPos(page_item.pos() + QPointF(data.rect[0], data.rect[1]))
        item.deleted.connect(lambda d: self._on_item_deleted(d.id, item))
        item.modified.connect(self._on_item_modified)
        item.edit_requested.connect(self._edit_text_box)
        item.selected_changed.connect(self.text_box_selected.emit)
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def _add_highlight_item(self, data: HighlightData, page_item: PdfPageItem) -> HighlightItem:
        scale = page_item.scale_x
        item = HighlightItem(data, scale=scale)
        x0 = min(data.rect[0], data.rect[2])
        y0 = min(data.rect[1], data.rect[3])
        item.setPos(page_item.pos() + QPointF(x0 * scale, y0 * scale))
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def _add_shape_item(self, data: ShapeData, page_item: PdfPageItem) -> ShapeItem:
        scale = page_item.scale_x
        item = ShapeItem(data, scale=scale)
        item.setPos(page_item.pos())
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def _add_freehand_item(self, data: FreehandData, page_item: PdfPageItem) -> FreehandItem:
        scale = page_item.scale_x
        item = FreehandItem(data, scale=scale)
        item.setPos(page_item.pos())
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def _add_image_item(self, data: ImageData, page_item: PdfPageItem) -> ImageItem:
        scale = page_item.scale_x
        item = ImageItem(data, scale=scale, page_item=page_item)
        item.setPos(page_item.pos() + QPointF(data.rect[0] * scale, data.rect[1] * scale))
        item.modified.connect(self._on_image_modified)
        item.deleted.connect(self._on_image_deleted)
        item.selected_changed.connect(lambda d: self.image_selected.emit(d))
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def _on_image_modified(self, data: ImageData) -> None:
        if self._engine:
            self._engine.annotation_manager.modify_image(data.id, data)
        self.document_modified.emit()

    def _on_image_deleted(self, data: ImageData) -> None:
        item = self._overlay_items.pop(data.id, None)
        if item is not None and item.scene():
            self._scene.removeItem(item)
        self.annotation_deleted.emit(data.id)
        if self._engine and self._engine.annotation_manager.get_image(data.id):
            self._engine.annotation_manager.remove_image(data.id)
        self.document_modified.emit()

    def add_image_at(self, page_idx: int, image_path: str, pt_pos: tuple[float, float]) -> None:
        if 0 <= page_idx < len(self._page_items):
            page_item = self._page_items[page_idx]
            pm = QPixmap(image_path)
            h_pts = 150.0
            if not pm.isNull() and pm.width() > 0:
                h_pts = max(30.0, min(page_item.pt_height - pt_pos[1] - 10.0, 150.0 * (pm.height() / pm.width())))
            current_op = self.current_properties.get("opacity", 1.0)
            if current_op is None:
                current_op = 1.0
            data = ImageData(
                id=str(uuid.uuid4()),
                page_index=page_idx,
                rect=(pt_pos[0], pt_pos[1], pt_pos[0] + 150.0, pt_pos[1] + h_pts),
                image_path=image_path,
                opacity=float(current_op),
            )
            item = self._add_image_item(data, page_item)
            item.setSelected(True)
            self.ensureVisible(item)
            self.annotation_added.emit(data)

    def remove_overlay_by_id(self, item_id: str) -> None:
        if item_id in self._overlay_items:
            item = self._overlay_items.pop(item_id)
            if item.scene():
                self._scene.removeItem(item)
