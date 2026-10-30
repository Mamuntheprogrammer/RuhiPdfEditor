"""
Right-side properties panel for the PDF Editor.

Shows context-sensitive controls (text typography, shape properties, annotations, etc.)
that dynamically change based on the currently selected tool or annotation.
Designed with a modern, sleek card layout inspired by professional design tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFontDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.toolbar import get_toggle_icon

if TYPE_CHECKING:
    from ui.i18n import I18n
    from ui.toolbar import Tool

# Curated palette presets for quick single-click selection (14 colors in 2 neat rows)
PRESET_COLORS = [
    # Row 1: Monochrome & Neutrals
    "#000000",  # Black
    "#334155",  # Slate
    "#64748b",  # Gray
    "#94a3b8",  # Light Gray
    "#cbd5e1",  # Silver
    "#e2e8f0",  # Soft White
    "#ffffff",  # Pure White
    # Row 2: Vibrant Accents
    "#dc2626",  # Red
    "#ea580c",  # Orange
    "#d97706",  # Amber
    "#16a34a",  # Green
    "#0284c7",  # Blue
    "#7c3aed",  # Purple
    "#db2777",  # Pink
]


class _ColorButton(QPushButton):
    """Modern button displaying a color swatch, hex code label, and opens QColorDialog."""

    color_changed = Signal(str)

    def __init__(self, initial: str = "#000000", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ColorPickerBtn")
        self._color = QColor(initial)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_appearance()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> str:
        """Currently selected hex colour string."""
        return self._color.name()

    @color.setter
    def color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self._update_appearance()

    def _update_appearance(self) -> None:
        hex_str = self._color.name().upper()
        self.setText(f"  {hex_str}   ·   Custom...")

        # Render rounded swatch icon
        pm = QPixmap(20, 20)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(160, 160, 160), 1))
        p.setBrush(QBrush(self._color))
        p.drawRoundedRect(QRectF(1, 1, 18, 18), 4, 4)
        p.end()

        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(20, 20))

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, "Choose Colour")
        if chosen.isValid():
            self._color = chosen
            self._update_appearance()
            self.color_changed.emit(self._color.name())


class _ColorPaletteRow(QWidget):
    """Grid of curated preset color chips with active selection indicator."""

    color_picked = Signal(str)

    def __init__(self, initial_color: str = "#000000", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}
        self._selected_color = initial_color.lower()

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setSpacing(6)

        cols_per_row = 7
        for idx, col_hex in enumerate(PRESET_COLORS):
            r = idx // cols_per_row
            c = idx % cols_per_row

            btn = QPushButton()
            btn.setFixedSize(28, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(col_hex.upper())
            btn.clicked.connect(lambda checked=False, ch=col_hex: self._on_btn_clicked(ch))

            self._buttons[col_hex.lower()] = btn
            grid.addWidget(btn, r, c)

        self._update_indicators()

    def _on_btn_clicked(self, col_hex: str) -> None:
        self.set_selected_color(col_hex)
        self.color_picked.emit(col_hex)

    def set_selected_color(self, hex_color: str) -> None:
        """Update active selection ring / indicator on matching preset."""
        norm = hex_color.strip().lower()
        if len(norm) == 7 and norm.startswith("#"):
            self._selected_color = norm
            self._update_indicators()

    def _update_indicators(self) -> None:
        for col_hex, btn in self._buttons.items():
            is_active = (col_hex == self._selected_color)
            qcol = QColor(col_hex)
            is_light = qcol.lightness() > 180

            if is_active:
                icon_col = "#334155" if is_light else "#ffffff"
                pm = QPixmap(14, 14)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                p.setPen(
                    QPen(
                        QColor(icon_col),
                        2.2,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                p.drawLine(QPointF(2, 7), QPointF(5.5, 11))
                p.drawLine(QPointF(5.5, 11), QPointF(12, 3))
                p.end()
                btn.setIcon(QIcon(pm))
                btn.setIconSize(QSize(14, 14))
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {col_hex}; border: 2px solid #0284c7; border-radius: 6px; }}"
                )
            else:
                btn.setIcon(QIcon())
                border_col = "#94a3b8" if is_light else "#cbd5e1"
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {col_hex}; border: 1.5px solid {border_col}; border-radius: 6px; }}"
                    f"QPushButton:hover {{ border: 2px solid #0284c7; }}"
                )


# ====================================================================== #
#  Panels for each tool category
# ====================================================================== #

class _TextPropertiesWidget(QWidget):
    """Font family, size, colour, bold, italic controls with modern card design."""

    font_changed = Signal(str)
    font_size_changed = Signal(float)
    color_changed = Signal(str)
    bold_changed = Signal(bool)
    italic_changed = Signal(bool)
    underline_changed = Signal(bool)
    strike_changed = Signal(bool)
    opacity_changed = Signal(float)

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Card container
        self.card = QFrame()
        self.card.setObjectName("PropertiesCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Title
        self._title_label = QLabel(i18n.t("properties"))
        self._title_label.setObjectName("CardTitle")
        card_layout.addWidget(self._title_label)

        # --- 1. Font Family ---
        font_header = QHBoxLayout()
        font_header.setContentsMargins(0, 0, 0, 0)
        self._font_label = QLabel(i18n.t("font_family"))
        self._font_label.setObjectName("SectionLabel")
        font_header.addWidget(self._font_label)
        font_header.addStretch()

        self.btn_system_font = QPushButton("🔤 System Font...")
        self.btn_system_font.setObjectName("SystemFontBtn")
        self.btn_system_font.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_system_font.setToolTip("Browse and choose from all installed Windows system fonts")
        self.btn_system_font.clicked.connect(self._choose_system_font)
        font_header.addWidget(self.btn_system_font)
        card_layout.addLayout(font_header)

        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.currentTextChanged.connect(self.font_changed.emit)
        card_layout.addWidget(self.font_combo)

        # --- 2. Font Size & Style (Side-by-side row) ---
        self._size_style_label = QLabel(i18n.t("font_size"))
        self._size_style_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._size_style_label)

        size_style_row = QHBoxLayout()
        size_style_row.setSpacing(6)

        # Prominent decrement button (-)
        self.btn_size_dec = QPushButton("−")
        self.btn_size_dec.setObjectName("SizeStepBtn")
        self.btn_size_dec.setFixedSize(34, 34)
        self.btn_size_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_size_dec.setToolTip(i18n.t("decrease_font_size"))
        f_dec = self.btn_size_dec.font()
        f_dec.setPointSize(14)
        f_dec.setBold(True)
        self.btn_size_dec.setFont(f_dec)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(1, 144)
        self.font_size_spin.setValue(14)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setFixedHeight(34)
        self.font_size_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.font_size_spin.valueChanged.connect(
            lambda v: self.font_size_changed.emit(float(v))
        )

        self.btn_size_dec.clicked.connect(self.font_size_spin.stepDown)

        # Prominent increment button (+)
        self.btn_size_inc = QPushButton("+")
        self.btn_size_inc.setObjectName("SizeStepBtn")
        self.btn_size_inc.setFixedSize(34, 34)
        self.btn_size_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_size_inc.setToolTip(i18n.t("increase_font_size"))
        f_inc = self.btn_size_inc.font()
        f_inc.setPointSize(14)
        f_inc.setBold(True)
        self.btn_size_inc.setFont(f_inc)
        self.btn_size_inc.clicked.connect(self.font_size_spin.stepUp)

        size_style_row.addWidget(self.btn_size_dec)
        size_style_row.addWidget(self.font_size_spin, 1)
        size_style_row.addWidget(self.btn_size_inc)

        # Modern toggle button for Bold with vector icon
        self.bold_btn = QPushButton()
        self.bold_btn.setObjectName("BoldToggleBtn")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(34, 34)
        self.bold_btn.setIcon(get_toggle_icon("bold"))
        self.bold_btn.setIconSize(QSize(18, 18))
        self.bold_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bold_btn.setToolTip(i18n.t("bold"))
        self.bold_btn.toggled.connect(self.bold_changed.emit)
        size_style_row.addWidget(self.bold_btn)

        # Modern toggle button for Italic with vector icon
        self.italic_btn = QPushButton()
        self.italic_btn.setObjectName("ItalicToggleBtn")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(34, 34)
        self.italic_btn.setIcon(get_toggle_icon("italic"))
        self.italic_btn.setIconSize(QSize(18, 18))
        self.italic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.italic_btn.setToolTip(i18n.t("italic"))
        self.italic_btn.toggled.connect(self.italic_changed.emit)
        size_style_row.addWidget(self.italic_btn)

        # Modern toggle button for Underline with vector icon
        self.underline_btn = QPushButton()
        self.underline_btn.setObjectName("UnderlineToggleBtn")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(34, 34)
        self.underline_btn.setIcon(get_toggle_icon("underline"))
        self.underline_btn.setIconSize(QSize(18, 18))
        self.underline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.underline_btn.setToolTip(i18n.t("tool_underline"))
        self.underline_btn.toggled.connect(self.underline_changed.emit)
        size_style_row.addWidget(self.underline_btn)

        # Modern toggle button for Strike with vector icon
        self.strike_btn = QPushButton()
        self.strike_btn.setObjectName("StrikeToggleBtn")
        self.strike_btn.setCheckable(True)
        self.strike_btn.setFixedSize(34, 34)
        self.strike_btn.setIcon(get_toggle_icon("strikethrough"))
        self.strike_btn.setIconSize(QSize(18, 18))
        self.strike_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.strike_btn.setToolTip(i18n.t("tool_strikethrough"))
        self.strike_btn.toggled.connect(self.strike_changed.emit)
        size_style_row.addWidget(self.strike_btn)

        card_layout.addLayout(size_style_row)

        # --- 3. Text Colour & Presets ---
        self._color_label = QLabel(i18n.t("text_color"))
        self._color_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._color_label)

        self.color_btn = _ColorButton("#000000")
        self.color_btn.color_changed.connect(self._on_color_changed)
        card_layout.addWidget(self.color_btn)

        self.palette_row = _ColorPaletteRow()
        self.palette_row.color_picked.connect(self._on_preset_picked)
        card_layout.addWidget(self.palette_row)

        # --- 4. Opacity ---
        self._opacity_label = QLabel(i18n.t("opacity"))
        self._opacity_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._opacity_label)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self._opacity_value_label = QLabel("100%")
        self._opacity_value_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self._opacity_value_label)
        card_layout.addLayout(opacity_row)

        outer_layout.addWidget(self.card)
        outer_layout.addStretch()

    def _on_color_changed(self, col: str) -> None:
        self.palette_row.set_selected_color(col)
        self.color_changed.emit(col)

    def _on_preset_picked(self, col: str) -> None:
        self.color_btn.color = col
        self.palette_row.set_selected_color(col)
        self.color_changed.emit(col)

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def _choose_system_font(self) -> None:
        """Open system font selection dialog and apply selected font properties."""
        curr_fam = self.font_combo.currentText()
        curr_size = self.font_size_spin.value()
        curr_font = QFont(curr_fam, curr_size)
        curr_font.setBold(self.bold_btn.isChecked())
        curr_font.setItalic(self.italic_btn.isChecked())
        ok, chosen_font = QFontDialog.getFont(curr_font, self, "Select System Font")
        if ok and chosen_font:
            family = chosen_font.family()
            if self.font_combo.findText(family) == -1:
                self.font_combo.addItem(family)
            self.font_combo.setCurrentText(family)
            if chosen_font.pointSize() > 0:
                self.font_size_spin.setValue(chosen_font.pointSize())
            self.bold_btn.setChecked(chosen_font.bold())
            self.italic_btn.setChecked(chosen_font.italic())
            self.font_changed.emit(family)
            self.font_size_changed.emit(float(self.font_size_spin.value()))
            self.bold_changed.emit(chosen_font.bold())
            self.italic_changed.emit(chosen_font.italic())

    def update_translations(self, i18n: I18n) -> None:
        """Refresh labels after language change."""
        self._i18n = i18n
        self._title_label.setText(i18n.t("properties"))
        self._font_label.setText(i18n.t("font_family"))
        self._size_style_label.setText(i18n.t("font_size"))
        self._color_label.setText(i18n.t("text_color"))
        self._opacity_label.setText(i18n.t("opacity"))
        self.bold_btn.setToolTip(i18n.t("bold"))
        self.italic_btn.setToolTip(i18n.t("italic"))
        self.btn_size_dec.setToolTip(i18n.t("decrease_font_size"))
        self.btn_size_inc.setToolTip(i18n.t("increase_font_size"))


class _ShapePropertiesWidget(QWidget):
    """Stroke colour, fill colour, stroke width, opacity."""

    stroke_color_changed = Signal(str)
    fill_color_changed = Signal(str)
    stroke_width_changed = Signal(float)
    opacity_changed = Signal(float)

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.card = QFrame()
        self.card.setObjectName("PropertiesCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Title
        self._title_label = QLabel(i18n.t("tool_rectangle"))
        self._title_label.setObjectName("CardTitle")
        card_layout.addWidget(self._title_label)

        # Stroke colour
        self._stroke_label = QLabel(i18n.t("stroke_color"))
        self._stroke_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._stroke_label)
        self.stroke_btn = _ColorButton("#0284c7")
        self.stroke_btn.color_changed.connect(self.stroke_color_changed.emit)
        card_layout.addWidget(self.stroke_btn)

        # Fill colour
        self._fill_label = QLabel(i18n.t("fill_color"))
        self._fill_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._fill_label)
        self.fill_btn = _ColorButton("#ffffff")
        self.fill_btn.color_changed.connect(self.fill_color_changed.emit)
        card_layout.addWidget(self.fill_btn)

        # Stroke width
        self._width_label = QLabel(i18n.t("stroke_width"))
        self._width_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._width_label)
        self.stroke_width_spin = QDoubleSpinBox()
        self.stroke_width_spin.setRange(0.5, 20.0)
        self.stroke_width_spin.setValue(2.0)
        self.stroke_width_spin.setSingleStep(0.5)
        self.stroke_width_spin.setSuffix(" px")
        self.stroke_width_spin.setFixedHeight(34)
        self.stroke_width_spin.valueChanged.connect(self.stroke_width_changed.emit)
        card_layout.addWidget(self.stroke_width_spin)

        # Opacity
        self._opacity_label = QLabel(i18n.t("opacity"))
        self._opacity_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._opacity_label)
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self._opacity_value_label = QLabel("100%")
        self._opacity_value_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self._opacity_value_label)
        card_layout.addLayout(opacity_row)

        outer_layout.addWidget(self.card)
        outer_layout.addStretch()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def update_translations(self, i18n: I18n) -> None:
        """Refresh labels after language change."""
        self._i18n = i18n
        self._stroke_label.setText(i18n.t("stroke_color"))
        self._fill_label.setText(i18n.t("fill_color"))
        self._width_label.setText(i18n.t("stroke_width"))
        self._opacity_label.setText(i18n.t("opacity"))


class _AnnotationPropertiesWidget(QWidget):
    """Colour, style (highlight/underline/strike), and opacity for annotations."""

    color_changed = Signal(str)
    opacity_changed = Signal(float)
    style_changed = Signal(str)

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.card = QFrame()
        self.card.setObjectName("PropertiesCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Title
        self._title_label = QLabel(i18n.t("tool_highlight"))
        self._title_label.setObjectName("CardTitle")
        card_layout.addWidget(self._title_label)

        # Style / Type row: Highlight | Underline | Strike
        self._style_label = QLabel("Annotation Style:")
        self._style_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._style_label)

        style_row = QHBoxLayout()
        style_row.setSpacing(6)
        self.btn_style_hl = QPushButton(i18n.t("tool_highlight") if i18n else "Highlight")
        self.btn_style_hl.setCheckable(True)
        self.btn_style_hl.setChecked(True)
        self.btn_style_hl.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_style_ul = QPushButton(i18n.t("tool_underline") if i18n else "Underline")
        self.btn_style_ul.setCheckable(True)
        self.btn_style_ul.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_style_st = QPushButton(i18n.t("tool_strikethrough") if i18n else "Strike")
        self.btn_style_st.setCheckable(True)
        self.btn_style_st.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_style = (
            "QPushButton { padding: 4px 8px; border: 1.5px solid #cbd5e1; border-radius: 4px; font-size: 11px; font-weight: 600; background: #ffffff; color: #334155; }"
            "QPushButton:hover { border-color: #0284c7; }"
            "QPushButton:checked { background: #0284c7; color: #ffffff; border-color: #0284c7; }"
        )
        for b in (self.btn_style_hl, self.btn_style_ul, self.btn_style_st):
            b.setStyleSheet(btn_style)

        self.btn_style_hl.clicked.connect(lambda: self._set_style("highlight"))
        self.btn_style_ul.clicked.connect(lambda: self._set_style("underline"))
        self.btn_style_st.clicked.connect(lambda: self._set_style("strikethrough"))

        style_row.addWidget(self.btn_style_hl)
        style_row.addWidget(self.btn_style_ul)
        style_row.addWidget(self.btn_style_st)
        card_layout.addLayout(style_row)

        # Colour
        self._color_label = QLabel(i18n.t("color"))
        self._color_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._color_label)
        self.color_btn = _ColorButton("#ffeb3b")
        self.color_btn.color_changed.connect(self.color_changed.emit)
        card_layout.addWidget(self.color_btn)

        # Preset highlight colors
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        hl_colors = ["#ffeb3b", "#4ade80", "#38bdf8", "#f472b6", "#fb923c"]
        for c in hl_colors:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"background-color: {c}; border: 1.5px solid #cbd5e1; border-radius: 11px;"
            )
            btn.clicked.connect(lambda checked=False, col=c: self._pick_preset(col))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        card_layout.addLayout(preset_row)

        # Opacity
        self._opacity_label = QLabel(i18n.t("opacity"))
        self._opacity_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._opacity_label)
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(45)
        self._opacity_value_label = QLabel("45%")
        self._opacity_value_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self._opacity_value_label)
        card_layout.addLayout(opacity_row)

        outer_layout.addWidget(self.card)
        outer_layout.addStretch()

    def _pick_preset(self, col: str) -> None:
        self.color_btn.color = col
        self.color_changed.emit(col)

    def _set_style(self, style_name: str) -> None:
        self.btn_style_hl.setChecked(style_name == "highlight")
        self.btn_style_ul.setChecked(style_name == "underline")
        self.btn_style_st.setChecked(style_name == "strikethrough")
        if style_name == "highlight":
            self.opacity_slider.setValue(45)
            self.color_btn.color = "#ffeb3b"
            self.color_changed.emit("#ffeb3b")
        else:
            self.opacity_slider.setValue(90)
            self.color_btn.color = "#ef4444"
            self.color_changed.emit("#ef4444")
        self.style_changed.emit(style_name)

    def set_annotation_type(self, style_name: str) -> None:
        self.btn_style_hl.setChecked(style_name == "highlight")
        self.btn_style_ul.setChecked(style_name == "underline")
        self.btn_style_st.setChecked(style_name == "strikethrough")
        if style_name == "highlight":
            self.opacity_slider.setValue(45)
        else:
            self.opacity_slider.setValue(90)

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def update_translations(self, i18n: I18n) -> None:
        """Refresh labels after language change."""
        self._i18n = i18n
        self._color_label.setText(i18n.t("color"))
        self._opacity_label.setText(i18n.t("opacity"))


class _ImagePropertiesWidget(QWidget):
    """Opacity control for inserted images."""

    opacity_changed = Signal(float)

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.card = QFrame()
        self.card.setObjectName("PropertiesCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        self._title_label = QLabel(i18n.t("tool_image"))
        self._title_label.setObjectName("CardTitle")
        card_layout.addWidget(self._title_label)

        self._opacity_label = QLabel(i18n.t("opacity"))
        self._opacity_label.setObjectName("SectionLabel")
        card_layout.addWidget(self._opacity_label)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(8)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self._opacity_value_label = QLabel("100%")
        self._opacity_value_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self._opacity_value_label)
        card_layout.addLayout(opacity_row)

        outer_layout.addWidget(self.card)
        outer_layout.addStretch()

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_value_label.setText(f"{value}%")
        self.opacity_changed.emit(value / 100.0)

    def update_translations(self, i18n: I18n) -> None:
        """Refresh labels after language change."""
        self._i18n = i18n
        self._opacity_label.setText(i18n.t("opacity"))


class _EmptyPropertiesWidget(QWidget):
    """Subtle placeholder shown when no element is selected."""

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        card = QFrame()
        card.setObjectName("PropertiesCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 24, 16, 24)
        card_layout.setSpacing(8)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("⚙️")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_icon = icon_label.font()
        f_icon.setPointSize(24)
        icon_label.setFont(f_icon)
        card_layout.addWidget(icon_label)

        self.title_lbl = QLabel(i18n.t("properties"))
        self.title_lbl.setObjectName("CardTitle")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_lbl)

        self.hint_lbl = QLabel("Select an element or pick a tool from the toolbar to adjust formatting.")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_lbl.setWordWrap(True)
        self.hint_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        card_layout.addWidget(self.hint_lbl)

        outer_layout.addWidget(card)
        outer_layout.addStretch()


# ====================================================================== #
#  PropertiesPanel (public)
# ====================================================================== #

# Index constants for the stacked widget
_IDX_TEXT = 0
_IDX_SHAPE = 1
_IDX_ANNOTATION = 2
_IDX_IMAGE = 3
_IDX_EMPTY = 4


class PropertiesPanel(QDockWidget):
    """Right panel showing properties for the current tool / selection.

    Internally uses a :class:`QStackedWidget` to show the appropriate
    property sub-panel for the active tool.
    """

    # ---- Forwarded signals ---- #
    font_changed = Signal(str)
    font_size_changed = Signal(float)
    color_changed = Signal(str)
    bold_changed = Signal(bool)
    italic_changed = Signal(bool)
    underline_changed = Signal(bool)
    strike_changed = Signal(bool)
    annotation_type_changed = Signal(str)
    stroke_color_changed = Signal(str)
    fill_color_changed = Signal(str)
    stroke_width_changed = Signal(float)
    opacity_changed = Signal(float)

    def __init__(self, i18n: I18n, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self._i18n = i18n
        self.setObjectName("PropertiesPanel")
        self.setMinimumWidth(270)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Container
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # Sub-panels
        self._text_panel = _TextPropertiesWidget(i18n)
        self._shape_panel = _ShapePropertiesWidget(i18n)
        self._annotation_panel = _AnnotationPropertiesWidget(i18n)
        self._image_panel = _ImagePropertiesWidget(i18n)
        self._empty_panel = _EmptyPropertiesWidget(i18n)

        self._stack.addWidget(self._text_panel)         # 0
        self._stack.addWidget(self._shape_panel)        # 1
        self._stack.addWidget(self._annotation_panel)   # 2
        self._stack.addWidget(self._image_panel)        # 3
        self._stack.addWidget(self._empty_panel)        # 4

        main_layout.addWidget(self._stack)
        self.setWidget(container)

        # Forward signals from sub-panels
        self._text_panel.font_changed.connect(self.font_changed.emit)
        self._text_panel.font_size_changed.connect(self.font_size_changed.emit)
        self._text_panel.color_changed.connect(self.color_changed.emit)
        self._text_panel.bold_changed.connect(self.bold_changed.emit)
        self._text_panel.italic_changed.connect(self.italic_changed.emit)
        self._text_panel.underline_changed.connect(self.underline_changed.emit)
        self._text_panel.strike_changed.connect(self.strike_changed.emit)
        self._text_panel.opacity_changed.connect(self.opacity_changed.emit)

        self._shape_panel.stroke_color_changed.connect(self.stroke_color_changed.emit)
        self._shape_panel.fill_color_changed.connect(self.fill_color_changed.emit)
        self._shape_panel.stroke_width_changed.connect(self.stroke_width_changed.emit)
        self._shape_panel.opacity_changed.connect(self.opacity_changed.emit)

        self._annotation_panel.color_changed.connect(self.color_changed.emit)
        self._annotation_panel.opacity_changed.connect(self.opacity_changed.emit)
        self._annotation_panel.style_changed.connect(self.annotation_type_changed.emit)

        self._image_panel.opacity_changed.connect(self.opacity_changed.emit)

        # Default: empty
        self._stack.setCurrentIndex(_IDX_EMPTY)
        self.update_translations(i18n)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def show_text_properties(self, data) -> None:
        """Switch to text properties and populate with data from the selected text box."""
        self._stack.setCurrentIndex(_IDX_TEXT)
        self._text_panel.setEnabled(True)
        self._text_panel.font_combo.blockSignals(True)
        self._text_panel.font_size_spin.blockSignals(True)
        self._text_panel.bold_btn.blockSignals(True)
        self._text_panel.italic_btn.blockSignals(True)
        self._text_panel.underline_btn.blockSignals(True)
        self._text_panel.strike_btn.blockSignals(True)
        self._text_panel.opacity_slider.blockSignals(True)

        if hasattr(data, "font_family") and data.font_family:
            if self._text_panel.font_combo.findText(data.font_family) == -1:
                self._text_panel.font_combo.addItem(data.font_family)
            self._text_panel.font_combo.setCurrentText(data.font_family)
        if hasattr(data, "font_size") and data.font_size:
            self._text_panel.font_size_spin.setValue(int(data.font_size))
        if hasattr(data, "color") and data.color:
            self._text_panel.color_btn.color = data.color
            self._text_panel.palette_row.set_selected_color(data.color)
        if hasattr(data, "bold"):
            self._text_panel.bold_btn.setChecked(bool(data.bold))
        if hasattr(data, "italic"):
            self._text_panel.italic_btn.setChecked(bool(data.italic))
        if hasattr(data, "underline"):
            self._text_panel.underline_btn.setChecked(bool(data.underline))
        if hasattr(data, "strikethrough"):
            self._text_panel.strike_btn.setChecked(bool(data.strikethrough))
        if hasattr(data, "opacity") and data.opacity is not None:
            self._text_panel.opacity_slider.setValue(int(data.opacity * 100))

        self._text_panel.font_combo.blockSignals(False)
        self._text_panel.font_size_spin.blockSignals(False)
        self._text_panel.bold_btn.blockSignals(False)
        self._text_panel.italic_btn.blockSignals(False)
        self._text_panel.underline_btn.blockSignals(False)
        self._text_panel.strike_btn.blockSignals(False)
        self._text_panel.opacity_slider.blockSignals(False)

    def show_shape_properties(self, data) -> None:
        """Switch to shape properties and populate controls."""
        self._stack.setCurrentIndex(_IDX_SHAPE)
        if hasattr(data, "stroke_color") and data.stroke_color:
            self._shape_panel.stroke_btn.color = data.stroke_color
        if hasattr(data, "fill_color") and data.fill_color:
            self._shape_panel.fill_btn.color = data.fill_color
        if hasattr(data, "stroke_width") and data.stroke_width:
            self._shape_panel.stroke_width_spin.setValue(float(data.stroke_width))

    def show_annotation_properties(self, data) -> None:
        """Switch to annotation properties and populate controls."""
        self._stack.setCurrentIndex(_IDX_ANNOTATION)
        if hasattr(data, "annotation_type") and data.annotation_type:
            self._annotation_panel.set_annotation_type(data.annotation_type)
        if hasattr(data, "color") and data.color:
            self._annotation_panel.color_btn.color = data.color
        if hasattr(data, "opacity") and data.opacity:
            self._annotation_panel.opacity_slider.setValue(int(data.opacity * 100))

    def show_image_properties(self, data) -> None:
        """Switch to image properties and populate controls."""
        self._stack.setCurrentIndex(_IDX_IMAGE)
        if hasattr(data, "opacity") and data.opacity is not None:
            self._image_panel.opacity_slider.setValue(int(data.opacity * 100))

    def show_empty(self) -> None:
        """Switch to empty view when nothing is selected."""
        self._stack.setCurrentIndex(_IDX_EMPTY)

    def set_tool(self, tool: Tool) -> None:
        """Switch the properties panel to show relevant controls."""
        from ui.toolbar import Tool as ToolEnum

        mapping: dict[ToolEnum, int] = {
            ToolEnum.SELECT: _IDX_EMPTY,
            ToolEnum.TEXT: _IDX_TEXT,
            ToolEnum.HIGHLIGHT: _IDX_ANNOTATION,
            ToolEnum.UNDERLINE: _IDX_ANNOTATION,
            ToolEnum.STRIKETHROUGH: _IDX_ANNOTATION,
            ToolEnum.RECTANGLE: _IDX_SHAPE,
            ToolEnum.LINE: _IDX_SHAPE,
            ToolEnum.ARROW: _IDX_SHAPE,
            ToolEnum.FREEHAND: _IDX_SHAPE,
            ToolEnum.IMAGE: _IDX_IMAGE,
            ToolEnum.SIGNATURE: _IDX_IMAGE,
        }
        idx = mapping.get(tool, _IDX_EMPTY)
        self._stack.setCurrentIndex(idx)

    def set_font_families(self, families: list[str]) -> None:
        """Populate the font family dropdown with bundled fonts and installed system fonts."""
        combo = self._text_panel.font_combo
        combo.blockSignals(True)
        current = combo.currentText()
        combo.clear()

        # Add bundled fonts first
        all_families = list(families)

        # Append system fonts from QFontDatabase without duplicates
        try:
            sys_families = sorted(QFontDatabase.families())
            for sf in sys_families:
                if sf not in all_families and not sf.startswith("@"):
                    all_families.append(sf)
        except Exception:
            pass

        combo.addItems(all_families)
        if current and current in all_families:
            combo.setCurrentText(current)
        elif families:
            combo.setCurrentText(families[0])
        combo.blockSignals(False)

    def get_text_properties(self) -> dict:
        """Return current text properties as a dict."""
        return {
            "font_family": self._text_panel.font_combo.currentText(),
            "font_size": float(self._text_panel.font_size_spin.value()),
            "color": self._text_panel.color_btn.color,
            "bold": self._text_panel.bold_btn.isChecked(),
            "italic": self._text_panel.italic_btn.isChecked(),
            "underline": self._text_panel.underline_btn.isChecked(),
            "strikethrough": self._text_panel.strike_btn.isChecked(),
        }

    def get_shape_properties(self) -> dict:
        """Return current shape properties as a dict."""
        return {
            "stroke_color": self._shape_panel.stroke_btn.color,
            "fill_color": self._shape_panel.fill_btn.color,
            "stroke_width": self._shape_panel.stroke_width_spin.value(),
            "opacity": self._shape_panel.opacity_slider.value() / 100.0,
        }

    def get_annotation_properties(self) -> dict:
        """Return current annotation properties as a dict."""
        style = "highlight"
        if self._annotation_panel.btn_style_ul.isChecked():
            style = "underline"
        elif self._annotation_panel.btn_style_st.isChecked():
            style = "strikethrough"
        return {
            "color": self._annotation_panel.color_btn.color,
            "opacity": self._annotation_panel.opacity_slider.value() / 100.0,
            "annotation_type": style,
        }

    def update_translations(self, i18n: I18n) -> None:
        """Refresh all labels after a language change."""
        self._i18n = i18n
        self.setWindowTitle(i18n.t("properties"))
        self._text_panel.update_translations(i18n)
        self._shape_panel.update_translations(i18n)
        self._annotation_panel.update_translations(i18n)
        self._image_panel.update_translations(i18n)
