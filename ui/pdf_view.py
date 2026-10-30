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
import uuid
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QPointF, QRect, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
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
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QInputDialog,
    QLineEdit,
    QMenu,
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

        # Selection outline
        box = QRectF(0, 0, self.rect_w, self.rect_h)
        painter.setPen(QPen(QColor("#0284c7"), 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(2, 132, 199, 35)))
        painter.drawRoundedRect(box, 3, 3)

        # Delete '✕' button in red
        btn_s = 14.0
        btn_rect = QRectF(self.rect_w + 3, 1, btn_s, btn_s)
        painter.setBrush(QBrush(QColor("#ef4444")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(btn_rect, 2, 2)
        painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
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
            # Active selected/hovered state: prominent dashed blue border + handles + delete '✕'
            painter.setPen(QPen(QColor("#0284c7"), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(2, 132, 199, 22)))
            painter.drawRoundedRect(rect, 3, 3)

            # Corner handles
            painter.setBrush(QBrush(QColor("#0284c7")))
            painter.setPen(Qt.PenStyle.NoPen)
            hs = 4.0
            painter.drawRect(QRectF(0, 0, hs, hs))
            painter.drawRect(QRectF(rect.width() - hs, 0, hs, hs))
            painter.drawRect(QRectF(0, rect.height() - hs, hs, hs))
            painter.drawRect(QRectF(rect.width() - hs, rect.height() - hs, hs, hs))

            # Red '✕' delete button in top-right corner
            close_size = 14.0
            close_rect = QRectF(rect.width() - close_size - 2, 2, close_size, close_size)
            painter.setBrush(QBrush(QColor("#ef4444")))
            painter.drawRoundedRect(close_rect, 2, 2)
            painter.setPen(QPen(Qt.GlobalColor.white, 1.5))
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
            # Idle state on canvas: subtle editor mark so user knows this text is re-editable!
            # (Note: this mark is in the editor ONLY; when saved to PDF, pure text is burned with NO mark)
            painter.setPen(QPen(QColor(2, 132, 199, 130), 1.0, Qt.PenStyle.DotLine))
            painter.setBrush(QBrush(QColor(2, 132, 199, 10)))
            painter.drawRoundedRect(rect, 2, 2)

            # Tiny subtle edit dot in bottom-right corner to indicate re-editability
            painter.setBrush(QBrush(QColor(2, 132, 199, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(rect.width() - 3.5, rect.height() - 3.5), 1.5, 1.5)

        # Draw Bangla / Unicode text using HarfBuzz
        font = QFont(self.data.font_family)
        target_size = max(1.0, float(self.data.font_size) * self.scale_factor)
        font.setPointSizeF(target_size)
        font.setBold(self.data.bold)
        font.setItalic(self.data.italic)
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


class ImageItem(QGraphicsPixmapItem):
    """Inserted image or digital signature overlay."""

    def __init__(self, data: ImageData, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.data = data
        self.setZValue(4.0)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

        pixmap = QPixmap(data.image_path)
        if not pixmap.isNull():
            w = abs(data.rect[2] - data.rect[0]) if data.rect[2] > data.rect[0] else data.rect[2]
            h = abs(data.rect[3] - data.rect[1]) if data.rect[3] > data.rect[1] else data.rect[3]
            target_w = int(w * scale)
            target_h = int(h * scale)
            if target_w > 0 and target_h > 0:
                pixmap = pixmap.scaled(
                    target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self.setPixmap(pixmap)
            self.setOpacity(data.opacity)


# ====================================================================== #
#  PdfView (Main Graphics View)
# ====================================================================== #

class PdfView(QGraphicsView):
    """Main viewer and editor canvas for PDF documents."""

    page_changed = Signal(int)
    zoom_changed = Signal(float)
    text_box_added = Signal(TextBoxData)
    text_box_selected = Signal(object)  # emits TextBoxData when selected
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
        """Update property cache and apply immediately to any selected text box."""
        self.current_properties.update(props)

        # Apply to any currently selected text boxes
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
                it.prepareGeometryChange()
                it._sync_position()
                it.update()
                if self._engine:
                    self._engine.annotation_manager.modify_text_box(it.data.id, it.data)
                self.document_modified.emit()

    def _on_scene_selection_changed(self) -> None:
        """Notify properties panel when selection changes."""
        selected = self._scene.selectedItems()
        if len(selected) == 1 and isinstance(selected[0], TextBoxItem):
            self.text_box_selected.emit(selected[0].data)
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
            self.zoom_fit_width()

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
        if self._engine:
            for page_item in self._page_items:
                pixmap = self._engine.render_page(page_item.page_index, zoom=render_scale)
                page_item.set_rendered_pixmap(pixmap, render_scale)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / 1.25)

    def zoom_actual_size(self) -> None:
        """Actual size: 100% (1:1 PDF point scale)."""
        self.set_zoom(1.0)

    def zoom_fit_width(self) -> None:
        """Fit page width to viewport width."""
        if not self._page_items:
            return
        cur_idx = max(0, min(self._current_page_index, len(self._page_items) - 1))
        pt_w = self._page_items[cur_idx].pt_width
        view_w = self.viewport().width() - 40
        if pt_w > 0 and view_w > 50:
            target_zoom = max(0.2, min(5.0, view_w / pt_w))
            self.set_zoom(target_zoom)
        else:
            self.set_zoom(1.0)

    def zoom_fit_height(self) -> None:
        """Fit page height to viewport height."""
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

    def go_to_page(self, page_index: int) -> None:
        if 0 <= page_index < len(self._page_items):
            page_item = self._page_items[page_index]
            self.centerOn(page_item)
            self._current_page_index = page_index
            self.page_changed.emit(page_index)

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

        # Populate properties panel with this block's attributes
        is_bangla = any(0x0980 <= ord(c) <= 0x09FF for c in block.text)
        tb_data = TextBoxData(
            page_index=page_idx,
            rect=block.rect,
            text=block.text,
            font_family="Noto Sans Bengali" if is_bangla else "Noto Sans",
            font_size=block.font_size or 14.0,
            color="#000000",
        )
        self.text_box_selected.emit(tb_data)

    # ================================================================== #
    #  Mouse Events & Tool Interactions
    # ================================================================== #

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            target = self._get_page_under_pos(scene_pos)

            if target is not None:
                page_idx, page_item, local_pt = target

                # 1. Text Tool -> Check if existing text box was clicked, otherwise create new
                if self._current_tool == Tool.TEXT:
                    item = self.itemAt(event.pos())
                    if isinstance(item, TextBoxItem):
                        self._scene.clearSelection()
                        item.setSelected(True)
                        self.text_box_selected.emit(item.data)
                        self._edit_text_box(item)
                        return
                    self._create_inline_text_dialog(page_idx, page_item, local_pt)
                    return

                # 2. Select Tool -> Detect clicked single word or pass through
                elif self._current_tool == Tool.SELECT:
                    item = self.itemAt(event.pos())
                    if item is None or item == page_item:
                        if self._engine:
                            text_blocks = self._engine.get_text_blocks(page_idx, level="word")
                            hit_block = None
                            for tb in text_blocks:
                                x0, y0, x1, y1 = tb.rect
                                if (x0 - 2.0) <= local_pt.x() <= (x1 + 2.0) and (y0 - 2.0) <= local_pt.y() <= (y1 + 2.0):
                                    hit_block = tb
                                    break
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
                    if self._engine:
                        text_blocks = self._engine.get_text_blocks(page_idx, level="word")
                        for tb in text_blocks:
                            x0, y0, x1, y1 = tb.rect
                            if (x0 - 2.0) <= local_pt.x() <= (x1 + 2.0) and (y0 - 2.0) <= local_pt.y() <= (y1 + 2.0):
                                self._erase_text_block(page_idx, tb)
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
                if self._current_tool == Tool.FREEHAND:
                    self._freehand_points.append((local_pt.x(), local_pt.y()))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
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
        """Handle Delete/Backspace key and Undo/Redo shortcuts."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
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
        title = self._i18n.t("tool_redact") if self._i18n else "Redact & Replace"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text=block.text,
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
        )
        if dlg.exec():
            final_text = dlg.get_text()
            if final_text is not None:
                parent_win = self.window()
                font_fam = self.current_properties.get("font_family", "Noto Sans Bengali")
                font_sz = block.font_size or 12.0
                col = self.current_properties.get("color", "#000000")
                if hasattr(parent_win, "_undo_stack"):
                    cmd = RedactCommand(
                        self._engine,
                        page_idx,
                        block.rect,
                        replacement_text=final_text,
                        font_family=font_fam,
                        font_size=font_sz,
                        color=col,
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
                    )
                self.refresh_page(page_idx)
                self._clear_text_block_selection()
                self.document_modified.emit()

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
        """Prompt user for multi-line text with Enter for newline and Bangla phonetic support."""
        title = self._i18n.t("tool_text") if self._i18n else "Add Text"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text="",
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
        )
        if dlg.exec():
            final_text = dlg.get_text()
            if final_text and final_text.strip():
                font_fam = self.current_properties.get("font_family", "Noto Sans Bengali")
                font_sz = float(self.current_properties.get("font_size", 14.0))
                is_bold = bool(self.current_properties.get("bold", False))
                is_italic = bool(self.current_properties.get("italic", False))

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
                init_w = max(16.0, float(br.width()) + 16.0)
                init_h = max(8.0, float(br.height()) + 8.0)

                data = TextBoxData(
                    id=str(uuid.uuid4()),
                    page_index=page_idx,
                    rect=(local_pt.x(), local_pt.y(), local_pt.x() + init_w, local_pt.y() + init_h),
                    text=final_text,
                    font_family=font_fam,
                    font_size=font_sz,
                    color=self.current_properties.get("color", "#000000"),
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
                self.text_box_selected.emit(item.data)
                self.set_tool(Tool.SELECT)
                self.tool_switched.emit(Tool.SELECT)

    def _edit_text_box(self, item: TextBoxItem) -> None:
        """Edit existing text box via multi-line editor."""
        self._scene.clearSelection()
        item.setSelected(True)
        self.text_box_selected.emit(item.data)

        title = self._i18n.t("tool_text") if self._i18n else "Edit Text"
        dlg = MultiLineTextDialog(
            parent=self,
            title=title,
            initial_text=item.data.text,
            bangla_engine=self._bangla_engine,
            i18n=self._i18n,
        )
        if dlg.exec():
            final_text = dlg.get_text()
            if final_text is not None and final_text != item.data.text:
                item.data.text = final_text
                item.prepareGeometryChange()
                item._sync_position()
                item.update()
                if self._engine:
                    self._engine.annotation_manager.modify_text_box(item.data.id, item.data)
                self.text_box_selected.emit(item.data)
                self.document_modified.emit()

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
        item = ImageItem(data, scale=scale)
        item.setPos(page_item.pos() + QPointF(data.rect[0] * scale, data.rect[1] * scale))
        self._scene.addItem(item)
        self._overlay_items[data.id] = item
        return item

    def add_image_at(self, page_idx: int, image_path: str, pt_pos: tuple[float, float]) -> None:
        if 0 <= page_idx < len(self._page_items):
            page_item = self._page_items[page_idx]
            data = ImageData(
                id=str(uuid.uuid4()),
                page_index=page_idx,
                rect=(pt_pos[0], pt_pos[1], pt_pos[0] + 150.0, pt_pos[1] + 150.0),
                image_path=image_path,
                opacity=1.0,
            )
            self._add_image_item(data, page_item)
            self.annotation_added.emit(data)

    def remove_overlay_by_id(self, item_id: str) -> None:
        if item_id in self._overlay_items:
            item = self._overlay_items.pop(item_id)
            if item.scene():
                self._scene.removeItem(item)
