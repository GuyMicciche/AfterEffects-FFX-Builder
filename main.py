"""
After Effects FFX Builder
A PyQt6 GUI for building After Effects pseudo effect FFX preset files.
Requires ae_ffx.py in the same directory.
"""

import sys
import json
import os
import copy
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
    QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox, QGroupBox,
    QSplitter, QFileDialog, QMessageBox, QScrollArea, QFrame,
    QSizePolicy, QToolBar, QStatusBar, QColorDialog, QMenu,
    QAbstractItemView, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRect, QPoint, QMimeData
from PyQt6.QtGui import QIcon, QAction, QColor, QFont, QPixmap, QPainter, QBrush, QPen, QPolygon, QPalette, QDrag

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ae_ffx import generate_ffx_file


# ── path helpers ─────────────────────────────────────────────────────────────
def _desktop() -> str:
    """Return the user's Desktop folder cross-platform."""
    return str(Path.home() / "Desktop")


def _find_ae_preset_folder() -> str:
    """
    Search for the latest installed After Effects User Presets folder.
    Scans years 2040 down to 2014 and returns the first match found.
    Falls back to Desktop if AE is not installed.
    """
    docs  = Path.home() / "Documents"
    adobe = docs / "Adobe"
    if not adobe.exists():
        return _desktop()
    for year in range(2040, 2013, -1):
        ae_folder = adobe / f"After Effects {year}"
        if ae_folder.exists():
            preset_folder = ae_folder / "User Presets" / "GM FFX Builder"
            preset_folder.mkdir(parents=True, exist_ok=True)
            return str(preset_folder)
    return _desktop()


# ── palette ──────────────────────────────────────────────────────────────────
DARK_BG      = "#1e1e2e"
PANEL_BG     = "#252535"
ITEM_BG      = "#2a2a3e"
ACCENT       = "#7c6af7"
ACCENT_HOVER = "#9580ff"
TEXT         = "#cdd6f4"
TEXT_DIM     = "#6c7086"
BORDER       = "#383850"
RED          = "#f38ba8"

TYPE_COLORS = {
    "Group":    "#ffffff",
    "Label":    "#7d819d",
    "Text":     "#7d819d",
    "Slider":   "#7c6af7",
    "Angle":    "#89dceb",
    "Color":    "#f9e2af",
    "Checkbox": "#a6e3a1",
    "Layer":    "#f38ba8",
    "Point":    "#cba6f7",
    "Point3D":  "#b4befe",
    "Dropdown":    "#fab387",
    "endgroup": "#45475a",
}

TYPE_ICONS = {
    "Group":    "",
    # "Group":    "\u25b8",
    "Label":    "\u00A7",
    "Text":     "\uD835\uDE83",
    "Slider":   "\u2194",
    "Angle":    "\u2220",
    "Color":    "\u25a0",
    "Checkbox": "\u2611",
    "Layer":    "\u229f",
    "Point":    "\u271b",
    "Point3D":  "\u271b\u00b3",
    "Dropdown":    "\u25be",
    "endgroup": "\u25c4",
}

# endgroup is NOT listed -- it is auto-injected on export
CONTROL_TYPES = [
    "Group", "Label",
    # "Text",
    "Point", "Point3D",
    "Slider", "Angle", "Color", "Checkbox",
    "Layer", "Dropdown",
]

# ── stylesheet ───────────────────────────────────────────────────────────────
SS = (
    "QMainWindow, QWidget {"
    f"background-color:{DARK_BG}; color:{TEXT};"
    "font-family:'Segoe UI','Inter',sans-serif; font-size:13px;}"

    f"QSplitter::handle {{background-color:{BORDER}; width:2px;}}"

    f"QTreeWidget {{background-color:{PANEL_BG}; border:1px solid {BORDER};"
    "border-radius:6px; outline:none; padding:4px; show-decoration-selected:1;}"
    f"QTreeWidget::item {{height:26px; padding-left:2px; border-radius:4px;}}"
    f"QTreeWidget::item:selected {{background-color:{ACCENT}; color:white;}}"
    f"QTreeWidget::item:hover:!selected {{background-color:{ITEM_BG};}}"
    f"QTreeWidget::branch {{background-color:{PANEL_BG};}}"
    "QTreeWidget::branch:has-children:!has-siblings:closed,"
    "QTreeWidget::branch:closed:has-children:has-siblings"
    "{border-image:none; image:none;}"
    "QTreeWidget::branch:open:has-children:!has-siblings,"
    "QTreeWidget::branch:open:has-children:has-siblings"
    "{border-image:none; image:none;}"

    f"QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{"
    f"background-color:{ITEM_BG}; border:1px solid {BORDER}; border-radius:4px;"
    f"padding:3px 7px; color:{TEXT}; selection-background-color:{ACCENT};"
    "min-height:22px; max-height:26px;}"
    f"QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus"
    f"{{border:1px solid {ACCENT};}}"
    f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,"
    f"QSpinBox::up-button, QSpinBox::down-button"
    f"{{background-color:{BORDER}; width:16px; border-radius:2px;}}"
    f"QComboBox::drop-down {{border:none; width:24px;}}"
    f"QComboBox QAbstractItemView {{background-color:{ITEM_BG}; border:1px solid {BORDER};"
    f"selection-background-color:{ACCENT};}}"

    f"QCheckBox {{spacing:8px;}}"
    f"QCheckBox::indicator {{width:15px; height:15px; border:1px solid {BORDER};"
    f"border-radius:3px; background-color:{ITEM_BG};}}"
    f"QCheckBox::indicator:checked {{background-color:{ACCENT}; border-color:{ACCENT};}}"

    f"QGroupBox {{border:1px solid {BORDER}; border-radius:6px; margin-top:10px;"
    f"padding-top:6px; font-weight:bold; color:{TEXT_DIM};}}"
    "QGroupBox::title {subcontrol-origin:margin; left:10px; padding:0 4px;}"

    f"QPushButton {{background-color:{ITEM_BG}; border:1px solid {BORDER};"
    "border-radius:5px; padding:5px 12px; font-weight:500;}"
    f"QPushButton:hover {{background-color:{BORDER}; border-color:{ACCENT};}}"
    f"QPushButton:pressed {{background-color:{ACCENT}; color:white;}}"
    f"QPushButton#accent {{background-color:{ACCENT}; border-color:{ACCENT};"
    "color:white; font-weight:600;}"
    f"QPushButton#accent:hover {{background-color:{ACCENT_HOVER};}}"
    f"QPushButton#danger {{border-color:{RED}; color:{RED};}}"
    f"QPushButton#danger:hover {{background-color:{RED}; color:white;}}"

    f"QLabel#sectionLabel {{color:{TEXT_DIM}; font-size:10px; font-weight:700; letter-spacing:1px;}}"

    f"QStatusBar {{background-color:{PANEL_BG}; border-top:1px solid {BORDER}; color:{TEXT_DIM};}}"
    f"QToolBar {{background-color:{PANEL_BG}; border-bottom:1px solid {BORDER}; spacing:4px; padding:4px;}}"
    f"QFrame#sep {{background-color:{BORDER}; max-height:1px; min-height:1px;}}"

    f"QMenu {{background-color:{ITEM_BG}; border:1px solid {BORDER}; border-radius:4px; padding:4px;}}"
    f"QMenu::item {{padding:4px 20px; border-radius:3px;}}"
    f"QMenu::item:selected {{background-color:{ACCENT}; color:white;}}"
    f"QMenu::separator {{background-color:{BORDER}; height:1px; margin:3px 0;}}"
)

# ── draggable control type button ─────────────────────────────────────────────
class DraggableTypeButton(QPushButton):
    def __init__(self, ctrl_type, label, parent=None):
        super().__init__(label, parent)
        self._ctrl_type = ctrl_type
        self._drag_start = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self._ctrl_type)
        drag.setMimeData(mime)

        # Render the button into a pixmap for the drag ghost
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())

        drag.exec(Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        super().mouseReleaseEvent(event)


# ── colour swatch ─────────────────────────────────────────────────────────────
class ColorSwatch(QPushButton):
    colorChanged = pyqtSignal(int, int, int)

    def __init__(self, r=255, g=255, b=255, parent=None):
        super().__init__(parent)
        self.r, self.g, self.b = r, g, b
        self.setFixedSize(48, 24)
        self._refresh()
        self.clicked.connect(self._pick)

    def _refresh(self):
        pix = QPixmap(46, 22)
        pix.fill(QColor(self.r, self.g, self.b))
        self.setIcon(QIcon(pix))
        self.setIconSize(QSize(46, 22))
        self.setText("")

    def _pick(self):
        col = QColorDialog.getColor(QColor(self.r, self.g, self.b), self)
        if col.isValid():
            self.r, self.g, self.b = col.red(), col.green(), col.blue()
            self._refresh()
            self.colorChanged.emit(self.r, self.g, self.b)

    def set_rgb(self, r, g, b):
        self.r, self.g, self.b = r, g, b
        self._refresh()


# ── property editor ───────────────────────────────────────────────────────────
class PropertyEditor(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = False
        self._current_item = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._title = QLabel("No selection")
        self._title.setStyleSheet(
            f"font-size:14px; font-weight:700; color:{TEXT}; padding:12px 16px 6px 16px;")
        outer.addWidget(self._title)

        sep = QFrame(); sep.setObjectName("sep")
        outer.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(14, 6, 14, 6)
        self._layout.setSpacing(3)          # tight
        self._layout.addStretch()
        scroll.setWidget(self._content)

    # widget attrs that hold references to editor fields; cleared on each load
    _FIELD_ATTRS = (
        '_name', '_keyframes', '_hold', '_invisible',
        '_valid_min', '_valid_max', '_slider_min', '_slider_max',
        '_default', '_precision', '_percent', '_pixel',
        '_swatch', '_r', '_g', '_b',
        '_cb_label', '_px', '_py', '_pz',
        '_dropdown_content', '_dim',
    )

    def _clear(self):
        # delete stale widget attr references so _write_to_item never reads
        # from a deleteLater'd widget belonging to the previous selection
        for attr in self._FIELD_ATTRS:
            if hasattr(self, attr):
                delattr(self, attr)
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _row(self, label_text, widget):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setFixedWidth(100)
        lbl.setStyleSheet(f"color:{TEXT_DIM};")
        row.addWidget(lbl)
        row.addWidget(widget, 1)
        c = QWidget(); c.setLayout(row)
        self._layout.insertWidget(self._layout.count() - 1, c)
        return widget

    def _section(self, text):
        gap = QWidget(); gap.setFixedHeight(16)
        self._layout.insertWidget(self._layout.count() - 1, gap)
        lbl = QLabel(text.upper()); lbl.setObjectName("sectionLabel")
        self._layout.insertWidget(self._layout.count() - 1, lbl)
        sep = QFrame(); sep.setObjectName("sep"); sep.setFixedHeight(2)
        self._layout.insertWidget(self._layout.count() - 1, sep)
        g2 = QWidget(); g2.setFixedHeight(8)
        self._layout.insertWidget(self._layout.count() - 1, g2)

    def _dbl(self, val=0.0, lo=-1e9, hi=1e9, step=1.0, decimals=3):
        w = QDoubleSpinBox()
        w.setRange(lo, hi); w.setSingleStep(step)
        w.setDecimals(decimals); w.setValue(val)
        w.valueChanged.connect(self._emit)
        return w

    def _int(self, val=0, lo=0, hi=9999):
        w = QSpinBox(); w.setRange(lo, hi); w.setValue(val)
        w.valueChanged.connect(self._emit)
        return w

    def _check(self, checked=False):
        w = QCheckBox(); w.setChecked(checked)
        w.stateChanged.connect(self._emit)
        return w

    def _line(self, text=""):
        w = QLineEdit(text); w.textChanged.connect(self._emit)
        return w

    def _emit(self, *_):
        if not self._building:
            self._write_to_item()
            self.changed.emit()

    def load(self, tree_item: QTreeWidgetItem):
        self._building = True
        self._current_item = tree_item
        self._clear()
        data = tree_item.data(0, Qt.ItemDataRole.UserRole) or {}
        ctrl_type = data.get("type", "")
        icon = TYPE_ICONS.get(ctrl_type, "")
        label_text = ctrl_type if ctrl_type in ("Group") else f"{icon}  {ctrl_type}"
        self._title.setText(label_text)

        self._section("Identity")
        self._name = self._row("Name", self._line(data.get("name", "")))

        has_kf  = ctrl_type in ("Slider","Angle","Color","Checkbox","Point","Point3D","Dropdown")
        has_inv = ctrl_type in ("Slider","Angle","Color","Checkbox","Layer",
                                "Point","Point3D","Dropdown","Group","Label","Text")
        if has_kf or has_inv:
            self._section("Options")
        if has_kf:
            self._keyframes = self._row("Keyframes", self._check(data.get("keyframes", True)))
            self._hold      = self._row("Hold Keys",  self._check(data.get("hold", False)))
        if has_inv:
            self._invisible = self._row("Invisible",  self._check(data.get("invisible", False)))

        if ctrl_type == "Slider":
            self._section("Range")
            self._valid_min  = self._row("Valid Min",  self._dbl(data.get("valid_min", -100.0),-1e9,1e9))
            self._valid_max  = self._row("Valid Max",  self._dbl(data.get("valid_max",  100.0),-1e9,1e9))
            self._slider_min = self._row("Slider Min", self._dbl(data.get("slider_min",-100.0),-1e9,1e9))
            self._slider_max = self._row("Slider Max", self._dbl(data.get("slider_max", 100.0),-1e9,1e9))
            self._section("Default")
            self._default    = self._row("Default",    self._dbl(data.get("default_value",0.0),-1e9,1e9))
            self._section("Display")
            self._precision  = self._row("Precision",  self._int(data.get("precision",1),0,5))
            self._percent    = self._row("Percent",    self._check(data.get("percent",False)))
            self._pixel      = self._row("Pixel",      self._check(data.get("pixel",False)))

        elif ctrl_type == "Angle":
            self._section("Default")
            self._default = self._row("Default (°)",
                self._dbl(data.get("default_value",0.0),-36000,36000,1.0,2))

        elif ctrl_type == "Color":
            self._section("Default Color")
            self._swatch = ColorSwatch(data.get("red",255),data.get("green",255),data.get("blue",255))
            sw_h = QHBoxLayout(); sw_h.setContentsMargins(0,0,0,0); sw_h.setSpacing(8)
            sl = QLabel("Swatch"); sl.setFixedWidth(100); sl.setStyleSheet(f"color:{TEXT_DIM};")
            sw_h.addWidget(sl); sw_h.addWidget(self._swatch); sw_h.addStretch()
            sw_c = QWidget(); sw_c.setLayout(sw_h)
            self._layout.insertWidget(self._layout.count()-1, sw_c)
            self._r = self._row("Red",   self._int(data.get("red",   255),0,255))
            self._g = self._row("Green", self._int(data.get("green", 255),0,255))
            self._b = self._row("Blue",  self._int(data.get("blue",  255),0,255))

            def on_swatch(r,g,b):
                self._building = True
                self._r.setValue(r); self._g.setValue(g); self._b.setValue(b)
                self._building = False
                self._emit()
            self._swatch.colorChanged.connect(on_swatch)

            def on_spin(*_):
                if not self._building:
                    self._swatch.set_rgb(self._r.value(),self._g.value(),self._b.value())
            self._r.valueChanged.connect(on_spin)
            self._g.valueChanged.connect(on_spin)
            self._b.valueChanged.connect(on_spin)

        elif ctrl_type == "Checkbox":
            self._section("Default & Label")
            self._default  = self._row("Checked",   self._check(data.get("default_value",False)))
            self._cb_label = self._row("Box Label",  self._line(data.get("Label","")))

        elif ctrl_type == "Layer":
            self._section("Default")
            self._default = self._row("Self Layer", self._check(data.get("default_value",False)))

        elif ctrl_type == "Point":
            self._section("Default Position (%)")
            self._px = self._row("X %", self._dbl(data.get("percentX",50.0),0,100,0.5,2))
            self._py = self._row("Y %", self._dbl(data.get("percentY",50.0),0,100,0.5,2))

        elif ctrl_type == "Point3D":
            self._section("Default Position (%)")
            self._px = self._row("X %", self._dbl(data.get("percentX",50.0),0,100,0.5,2))
            self._py = self._row("Y %", self._dbl(data.get("percentY",50.0),0,100,0.5,2))
            self._pz = self._row("Z %", self._dbl(data.get("percentZ", 0.0),0,100,0.5,2))

        elif ctrl_type == "Dropdown":
            self._section("Items")
            hint = QLabel("Pipe-separated  e.g.  One|Two|Three")
            hint.setStyleSheet(f"color:{TEXT_DIM}; font-size:11px;")
            self._layout.insertWidget(self._layout.count()-1, hint)
            self._dropdown_content = self._row("Items",
                self._line(data.get("content","Option 1|Option 2")))
            self._section("Default")
            self._default = self._row("Default Index",
                self._int(data.get("default_value",1),1,999))

        elif ctrl_type in ("Label","Text"):
            self._section("Display")
            self._dim = self._row("Dimmed", self._check(data.get("dim",False)))

        self._building = False

    def _write_to_item(self):
        if not self._current_item:
            return
        data = self._current_item.data(0, Qt.ItemDataRole.UserRole) or {}
        ctrl_type = data.get("type","")

        if hasattr(self,"_name"):       data["name"]      = self._name.text()
        if hasattr(self,"_keyframes"):  data["keyframes"] = self._keyframes.isChecked()
        if hasattr(self,"_hold"):       data["hold"]      = self._hold.isChecked()
        if hasattr(self,"_invisible"):  data["invisible"] = self._invisible.isChecked()

        if ctrl_type == "Slider":
            data["valid_min"]     = self._valid_min.value()
            data["valid_max"]     = self._valid_max.value()
            data["slider_min"]    = self._slider_min.value()
            data["slider_max"]    = self._slider_max.value()
            data["default_value"] = self._default.value()
            data["precision"]     = self._precision.value()
            data["percent"]       = self._percent.isChecked()
            data["pixel"]         = self._pixel.isChecked()
        elif ctrl_type == "Angle":
            data["default_value"] = self._default.value()
        elif ctrl_type == "Color":
            data["red"]   = self._r.value()
            data["green"] = self._g.value()
            data["blue"]  = self._b.value()
        elif ctrl_type == "Checkbox":
            data["default_value"] = self._default.isChecked()
            data["label"]         = self._cb_label.text()
        elif ctrl_type == "Layer":
            data["default_value"] = self._default.isChecked()
        elif ctrl_type == "Point":
            data["percentX"] = self._px.value()
            data["percentY"] = self._py.value()
        elif ctrl_type == "Point3D":
            data["percentX"] = self._px.value()
            data["percentY"] = self._py.value()
            data["percentZ"] = self._pz.value()
        elif ctrl_type == "Dropdown":
            data["content"]       = self._dropdown_content.text()
            data["default_value"] = self._default.value()
        elif ctrl_type in ("Label","Text"):
            data["dim"] = self._dim.isChecked()

        self._current_item.setData(0, Qt.ItemDataRole.UserRole, data)
        name = data.get("name","") or ctrl_type
        icon = TYPE_ICONS.get(ctrl_type,"?")
        # keep expand arrow state for groups
        if ctrl_type == "Group":
            old = self._current_item.text(0)
            arrow = "\u25be" if "\u25be" in old else "\u25b8"
            self._current_item.setText(0, f"{name}")
        else:
            self._current_item.setText(0, f"{icon}  {name}")

    def clear(self):
        self._current_item = None
        self._clear()
        self._title.setText("No selection")


# ── tree with custom drawn branch arrows ──────────────────────────────────────
class ControlTree(QTreeWidget):
    """Draws its own triangle expand/collapse indicators."""

    deletePressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.deletePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            return
        target = self.itemAt(event.position().toPoint())
        if target is None:
            super().dragMoveEvent(event)
            return
        indicator = self.dropIndicatorPosition()
        from PyQt6.QtWidgets import QAbstractItemView as _AIV
        if indicator == _AIV.DropIndicatorPosition.OnItem:
            data = target.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") != "Group":
                event.ignore()
                return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        # ── external button drag ──────────────────────────────────────────
        if event.mimeData().hasText() and event.source() is not self:
            ctrl_type = event.mimeData().text()
            target = self.itemAt(event.position().toPoint())
            indicator = self.dropIndicatorPosition()
            from PyQt6.QtWidgets import QAbstractItemView as _AIV
            if target is not None:
                if indicator == _AIV.DropIndicatorPosition.OnItem:
                    # dropped directly onto a group -- select it so _add_control inserts inside
                    data = target.data(0, Qt.ItemDataRole.UserRole) or {}
                    if data.get("type") == "Group":
                        self.setCurrentItem(target)
                    else:
                        # dropped onto a non-group item -- insert after it
                        self.setCurrentItem(target)
                else:
                    # dropped between items -- select the item above the gap
                    self.setCurrentItem(target)
            else:
                # dropped on empty space -- deselect so it appends at root
                self.clearSelection()
            self.window()._add_control(ctrl_type)
            event.acceptProposedAction()
            return

        # ── internal tree reorder ─────────────────────────────────────────
        target = self.itemAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()
        from PyQt6.QtWidgets import QAbstractItemView as _AIV
        if target is not None and indicator == _AIV.DropIndicatorPosition.OnItem:
            data = target.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") != "Group":
                event.ignore()
                return
        super().dropEvent(event)
        if target is not None and indicator == _AIV.DropIndicatorPosition.OnItem:
            target.setExpanded(True)

    def drawBranches(self, painter: QPainter, rect: QRect, index) -> None:
        super().drawBranches(painter, rect, index)
        item = self.itemFromIndex(index)
        if not item or not item.childCount():
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(TEXT_DIM)))
        cx = rect.right() - 10
        cy = rect.center().y()
        s  = 4
        if item.isExpanded():
            pts = QPolygon([QPoint(cx-s, cy-s//2), QPoint(cx+s, cy-s//2), QPoint(cx, cy+s)])
        else:
            pts = QPolygon([QPoint(cx-s//2, cy-s), QPoint(cx+s, cy), QPoint(cx-s//2, cy+s)])
        painter.drawPolygon(pts)


# ── main window ───────────────────────────────────────────────────────────────
class FFXBuilder(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFX Builder")
        self.resize(1100, 720)
        self.setMinimumSize(800, 500)
        self._setup_ui()
        self._tree.deletePressed.connect(self._delete)
        self._setup_toolbar()
        self.statusBar().showMessage("Ready")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith((".ffxbuild", ".json"))
                   for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith((".ffxbuild", ".json")):
                try:
                    state = self._read_state_from_file(path)
                except Exception as e:
                    QMessageBox.critical(self, "Load Error", str(e))
                    return
                self._tree.clear(); self._editor.clear()
                self._effect_name.setText(state.get("effect_name", ""))
                raw_mn = state.get("match_name", "")
                self._match_name.setText(raw_mn.removeprefix("Pseudo/"))
                self._load_controls(state.get("controls", []))
                self._tree.expandAll()
                self.statusBar().showMessage(f"Loaded: {path}")
                break

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # ── left ─────────────────────────────────────────────────────────
        left = QWidget(); left.setMinimumWidth(300)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 6, 12)
        ll.setSpacing(8)

        meta = QGroupBox("Effect Identity")
        ml   = QVBoxLayout(meta); ml.setSpacing(5)
        def meta_row(lbl_text, w):
            h = QHBoxLayout(); h.setSpacing(8)
            lb = QLabel(lbl_text); lb.setFixedWidth(90)
            lb.setStyleSheet(f"color:{TEXT_DIM};")
            h.addWidget(lb); h.addWidget(w, 1); ml.addLayout(h)
            return w
        self._effect_name = meta_row("Effect Name", QLineEdit("My Effect"))
        self._match_name  = meta_row("Match Name",  QLineEdit("MyEffect"))
        ll.addWidget(meta)

        ch = QHBoxLayout()
        cl = QLabel("CONTROLS"); cl.setObjectName("sectionLabel")
        ch.addWidget(cl); ch.addStretch()
        ll.addLayout(ch)

        btn_grid_widget = QWidget()
        btn_grid = QGridLayout(btn_grid_widget)
        btn_grid.setContentsMargins(0, 0, 0, 0)
        btn_grid.setSpacing(4)
        self._selected_type = CONTROL_TYPES[0]
        self._type_buttons = {}
        cols = 4
        DISPLAY_NAMES = {
            "Point3D":  "3D Point",
            # add any others you want to rename here
        }
        for idx, ctrl_type in enumerate(CONTROL_TYPES):
            row, col = divmod(idx, cols)
            color = TYPE_COLORS.get(ctrl_type, TEXT)
            icon  = TYPE_ICONS.get(ctrl_type, "")
            btn = QPushButton(f"{icon}  {DISPLAY_NAMES.get(ctrl_type, ctrl_type)}" if icon else DISPLAY_NAMES.get(ctrl_type, ctrl_type))
            btn = DraggableTypeButton(ctrl_type, f"{icon}  {DISPLAY_NAMES.get(ctrl_type, ctrl_type)}" if icon else DISPLAY_NAMES.get(ctrl_type, ctrl_type))
            btn.setStyleSheet(
                f"QPushButton {{color:{color}; font-size:11px; padding:3px 4px; text-align:center;}}"
                f"QPushButton:hover {{background-color:{ACCENT}; border-color:{ACCENT}; color:white; font-weight:700;}}"
            )
            btn.clicked.connect(lambda checked, t=ctrl_type: self._add_control(t))
            btn_grid.addWidget(btn, row, col)
            self._type_buttons[ctrl_type] = btn
        ll.addWidget(btn_grid_widget)


        self._tree = ControlTree()
        self._tree.setHeaderHidden(True)
        self._tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._tree.setIndentation(18)
        self._tree.itemSelectionChanged.connect(self._on_selection)
        self._tree.itemExpanded.connect(self._on_expanded)
        self._tree.itemCollapsed.connect(self._on_collapsed)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._context_menu)
        ll.addWidget(self._tree, 1)

        br = QHBoxLayout(); br.setSpacing(5)
        for label, slot in [("▲ Up",self._move_up),("▼ Down",self._move_down),
                             ("⊞ Dupe",self._duplicate),("✕ Delete",self._delete)]:
            b = QPushButton(label)
            if label.startswith("✕"): b.setObjectName("danger")
            b.clicked.connect(slot); br.addWidget(b)
        ll.addLayout(br)

        splitter.addWidget(left)

        # ── right ─────────────────────────────────────────────────────────
        right = QWidget(); right.setMinimumWidth(320)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0); rl.setSpacing(0)

        self._editor = PropertyEditor()
        self._editor.changed.connect(self._on_editor_changed)
        rl.addWidget(self._editor, 1)

        sep = QFrame(); sep.setObjectName("sep"); rl.addWidget(sep)

        er = QHBoxLayout(); er.setContentsMargins(16,8,16,8); er.setSpacing(8)
        for label, slot in [("💾 Save Project",self._save_project),
                             ("📂 Load Project",self._load_project)]:
            b = QPushButton(label); b.clicked.connect(slot); er.addWidget(b)
        er.addStretch()
        exp = QPushButton("⬆  Export FFX")
        exp.setObjectName("accent")
        exp.clicked.connect(self._export_ffx); er.addWidget(exp)
        rl.addLayout(er)

        splitter.addWidget(right)
        splitter.setSizes([400, 700])

    def _setup_toolbar(self):
        tb = self.addToolBar("Main"); tb.setMovable(False)
        for label, slot in [("New",self._new_project),
                             ("Load Project",self._load_project),
                             ("Save Project",self._save_project),
                             ("Export FFX",  self._export_ffx)]:
            act = QAction(label, self); act.triggered.connect(slot); tb.addAction(act)
            if label in ("New","Save Project"): tb.addSeparator()

    # ── tree helpers ──────────────────────────────────────────────────────────
    def _make_item(self, data: dict) -> QTreeWidgetItem:
        ctrl_type = data.get("type","Slider")
        name      = (data.get("name","") or ctrl_type)
        icon      = TYPE_ICONS.get(ctrl_type,"?")
        color     = TYPE_COLORS.get(ctrl_type, TEXT)
        label_text = name if ctrl_type in ("Group") else f"{icon}  {name}"
        item = QTreeWidgetItem([label_text])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        item.setForeground(0, QColor(color))
        if ctrl_type == "Group":
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        return item
    
    def _item_depth(self, item):
        d = 0
        while item.parent():
            d += 1
            item = item.parent()
        return d

    # Human-readable base names for auto-numbering
    _TYPE_BASE_NAMES = {
        'Point3D': '3D Point', 'Checkbox': 'Checkbox',
        'Dropdown': 'Dropdown', 'Label': 'Label', 'Text': 'Text',
        'Group': 'Group', 'Slider': 'Slider', 'Angle': 'Angle',
        'Color': 'Color', 'Layer': 'Layer', 'Point': 'Point',
    }

    def _next_name(self, ctrl_type: str) -> str:
        """Return e.g. 'Group 3' if two groups already exist in the tree."""
        base_name = self._TYPE_BASE_NAMES.get(ctrl_type, ctrl_type)
        # collect all names in use
        used = set()
        def walk(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                d = child.data(0, Qt.ItemDataRole.UserRole) or {}
                if d.get("type") == ctrl_type:
                    used.add(d.get("name", ""))
                walk(child)
        walk(self._tree.invisibleRootItem())
        if base_name not in used:
            return base_name
        n = 1
        while f"{base_name} {n}" in used:
            n += 1
        return f"{base_name} {n}"

    def _default_data(self, ctrl_type: str) -> dict:
        base = dict(type=ctrl_type, name=self._next_name(ctrl_type),
                    keyframes=True, hold=False, invisible=False)
        if ctrl_type == "Slider":
            base.update(default_value=0.0, valid_min=-100.0, valid_max=100.0,
                        slider_min=-100.0, slider_max=100.0, precision=2,
                        percent=False, pixel=False)
        elif ctrl_type == "Angle":  base.update(default_value=0.0)
        elif ctrl_type == "Color":  base.update(red=255, green=255, blue=255)
        elif ctrl_type == "Checkbox": base.update(default_value=False, label="")
        elif ctrl_type == "Layer":  base.update(default_value=False)
        elif ctrl_type == "Point":  base.update(percentX=50.0, percentY=50.0)
        elif ctrl_type == "Point3D": base.update(percentX=50.0, percentY=50.0, percentZ=0.0)
        elif ctrl_type == "Dropdown":  base.update(content="Option 1|Option 2|Option 3", default_value=1)
        elif ctrl_type in ("Label","Text"): base.update(dim=False)
        elif ctrl_type == "Group":  base.pop("keyframes",None); base.pop("hold",None)
        elif ctrl_type == "endgroup":
            for k in ("keyframes","hold","invisible"): base.pop(k,None)
        return base

    def _add_control(self, ctrl_type: str):
        item = self._make_item(self._default_data(ctrl_type))
        sel  = self._tree.selectedItems()
        if sel:
            s      = sel[0]
            s_data = s.data(0, Qt.ItemDataRole.UserRole) or {}
            s_is_group = s_data.get("type") == "Group"

            if s_is_group:
                # Adding a non-group control while a group is selected → append inside
                s.addChild(item)
                s.setExpanded(True)
            else:
                # Non-group selected → insert after it in the same parent
                p = s.parent() or self._tree.invisibleRootItem()
                p.insertChild(p.indexOfChild(s) + 1, item)
        else:
            self._tree.addTopLevelItem(item)
        self._tree.setCurrentItem(item)
        if item.parent():
            item.parent().setExpanded(True)
        self.statusBar().showMessage(f"Added {ctrl_type}")

    def _on_expanded(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "Group":
            txt = item.text(0)
            # item.setText(0, txt.replace("\u25b8", "\u25be"))  # ▸ -> ▾

    def _on_collapsed(self, item: QTreeWidgetItem):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "Group":
            txt = item.text(0)
            # item.setText(0, txt.replace("\u25be", "\u25b8"))  # ▾ -> ▸

    def _selected(self):
        items = self._tree.selectedItems()
        return items[0] if items else None
    
    def _selected_items(self):
        return self._tree.selectedItems()

    def _move_up(self):
        items = self._tree.selectedItems()
        if not items:
            return

        parents = {}
        for item in items:
            root = item.parent() or self._tree.invisibleRootItem()
            key = id(root)
            if key not in parents:
                parents[key] = {"root": root, "items": []}
            parents[key]["items"].append(item)

        for group_data in parents.values():
            root = group_data["root"]
            group = group_data["items"]
            group.sort(key=lambda i: root.indexOfChild(i))

            for item in group:
                idx = root.indexOfChild(item)
                if idx > 0 and root.child(idx - 1) not in group:
                    root.takeChild(idx)
                    root.insertChild(idx - 1, item)

        self._reselect_items(items)


    def _move_down(self):
        items = self._tree.selectedItems()
        if not items:
            return

        parents = {}
        for item in items:
            root = item.parent() or self._tree.invisibleRootItem()
            key = id(root)
            if key not in parents:
                parents[key] = {"root": root, "items": []}
            parents[key]["items"].append(item)

        for group_data in parents.values():
            root = group_data["root"]
            group = group_data["items"]
            group.sort(key=lambda i: root.indexOfChild(i), reverse=True)

            for item in group:
                idx = root.indexOfChild(item)
                if idx < root.childCount() - 1 and root.child(idx + 1) not in group:
                    root.takeChild(idx)
                    root.insertChild(idx + 1, item)
        
        self._reselect_items(items)


    def _duplicate(self):
        items = self._selected_items()
        if not items:
            return

        new_items = []
        self._tree.clearSelection()

        for item in items:
            new_item = self._duplicate_item_recursive(item, rename_top=True)
            root = item.parent() or self._tree.invisibleRootItem()
            root.insertChild(root.indexOfChild(item) + 1, new_item)
            new_items.append(new_item)

        self._reselect_items(new_items)

    def _duplicate_item_recursive(self, item: QTreeWidgetItem, rename_top: bool = True) -> QTreeWidgetItem:
        """Deep-clone a tree item. If rename_top is True, assigns a new unique name
        to the top-level duplicated item. Children of a Group keep their own names."""
        data = copy.deepcopy(item.data(0, Qt.ItemDataRole.UserRole))
        if rename_top:
            ctrl_type = data.get("type", "")
            data["name"] = self._next_name(ctrl_type)
        new_item = self._make_item(data)
        # Recursively clone children (for Groups)
        for i in range(item.childCount()):
            child_clone = self._duplicate_item_recursive(item.child(i), rename_top=False)
            new_item.addChild(child_clone)
        if item.isExpanded():
            new_item.setExpanded(True)
        return new_item

    def _delete(self):
        items = self._selected_items()
        if not items:
            return

        # Determine the best item to select after deletion.
        # Use the last selected item (lowest in tree) as the anchor.
        # Priority: next sibling -> previous sibling -> parent.
        anchor = items[-1]
        parent = anchor.parent() or self._tree.invisibleRootItem()
        idx    = parent.indexOfChild(anchor)
        # figure out successor before removing anything
        if parent.childCount() > len(items):
            # there will be siblings left -- try next, fall back to previous
            after = parent.child(idx + 1) if idx + 1 < parent.childCount() else None
            # skip siblings that are also being deleted
            if after and after in items:
                after = None
            if after is None and idx > 0:
                for i in range(idx - 1, -1, -1):
                    candidate = parent.child(i)
                    if candidate not in items:
                        after = candidate
                        break
        else:
            # all siblings are gone -- select parent (None if root)
            after = anchor.parent()

        for item in items:
            # skip child if its parent is also selected
            p = item.parent()
            skip = False
            while p:
                if p in items:
                    skip = True
                    break
                p = p.parent()
            if skip:
                continue
            root = item.parent() or self._tree.invisibleRootItem()
            root.removeChild(item)

        if after:
            self._tree.setCurrentItem(after)
            self._editor.load(after)
        else:
            self._editor.clear()

    def _reselect_items(self, items):
        self._tree.clearSelection()
        for item in items:
            item.setSelected(True)

    def _context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item: return
        menu = QMenu(self)
        menu.addAction("Duplicate", self._duplicate)
        menu.addAction("Move Up",   self._move_up)
        menu.addAction("Move Down", self._move_down)
        menu.addSeparator()
        menu.addAction("Delete",    self._delete)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ── sync ──────────────────────────────────────────────────────────────────
    def _on_selection(self):
        item = self._selected()
        if item: self._editor.load(item)
        else:    self._editor.clear()

    def _on_editor_changed(self):
        item = self._selected()
        if item:
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            self.statusBar().showMessage(f"Editing: {data.get('name','')}")

    # ── flatten ───────────────────────────────────────────────────────────────
    def _flatten(self, root_item=None) -> list:
        """Walk tree; mirrors pem structure: a group emits one group marker,
        then all its children (flat), then a single endgroup that closes it.
        Children do NOT get their own endgroup. Lowercases the type field so the
        generator always receives the lowercase strings it expects."""
        controls = []
        parent   = root_item or self._tree.invisibleRootItem()
        for i in range(parent.childCount()):
            item = parent.child(i)
            data = dict(item.data(0, Qt.ItemDataRole.UserRole) or {})
            ui_type = data.get("type", "")
            export_type = ui_type.lower()

            if export_type == "label":
                export_type = "text"

            data["type"] = export_type

            if export_type == "group":
                controls.append(data)
                controls.extend(self._flatten(item))
                controls.append({"type": "endgroup", "name": ""})
            else:
                controls.append(data)
        return controls

    # ── project ───────────────────────────────────────────────────────────────
    def _project_state(self):
        return {"effect_name": self._effect_name.text(),
                "match_name":  f"Pseudo/{self._match_name.text()}",
                "controls":    self._tree_to_list()}

    def _tree_to_list(self, parent=None) -> list:
        """Serialize the tree to a nested list for project save/load.
        Preserves original capitalized type strings and nests children under
        a 'children' key for Group items -- completely separate from _flatten()
        which is export-only."""
        result = []
        root = parent or self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = dict(item.data(0, Qt.ItemDataRole.UserRole) or {})
            if data.get("type") == "Group":
                data["children"] = self._tree_to_list(item)
            result.append(data)
        return result

    def _new_project(self):
        if QMessageBox.question(self,"New Project","Clear current project?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes:
            self._tree.clear(); self._editor.clear()
            self._effect_name.setText("My Effect")
            self._match_name.setText("MyEffect")
            self.statusBar().showMessage("New project")

    def _save_project(self):
        path,_ = QFileDialog.getSaveFileName(
            self,"Save Project",_desktop(),
            "FFX Builder Project (*.ffxbuild)")
        if not path: return
        with open(path,"w") as f: json.dump(self._project_state(), f, indent=2)
        self.statusBar().showMessage(f"Saved: {path}")

    def _load_project(self):
        path,_ = QFileDialog.getOpenFileName(
            self,"Load Project",_desktop(),
            "FFX Builder Project (*.ffxbuild);;JSON (*.json)")
        if not path: return
        try:
            state = self._read_state_from_file(path)
        except Exception as e:
            QMessageBox.critical(self,"Load Error",str(e)); return
        self._tree.clear(); self._editor.clear()
        self._effect_name.setText(state.get("effect_name",""))
        raw_mn = state.get("match_name","")
        self._match_name.setText(raw_mn.removeprefix("Pseudo/"))
        self._load_controls(state.get("controls",[]))
        self._tree.expandAll()
        self.statusBar().showMessage(f"Loaded: {path}")

    def _read_state_from_file(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def _load_controls(self, controls: list, parent_item=None):
        """Rebuild tree from nested project list saved by _tree_to_list."""
        for data in controls:
            ctrl_type = data.get("type", "")
            children  = data.pop("children", [])   # extract before making item
            item = self._make_item(data)
            if parent_item:
                parent_item.addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            if children:
                self._load_controls(children, item)

    # ── export ────────────────────────────────────────────────────────────────
    def _export_ffx(self):
        effect_name = self._effect_name.text().strip()
        match_name  = self._match_name.text().strip()
        if not effect_name:
            QMessageBox.warning(self,"Export","Effect Name is required."); return
        if not match_name:
            QMessageBox.warning(self,"Export","Match Name is required."); return
        if not self._flatten():
            QMessageBox.warning(self,"Export","Add at least one control."); return
        path,_ = QFileDialog.getSaveFileName(
            self,"Export FFX",
            os.path.join(_find_ae_preset_folder(), f"{effect_name}.ffx"),
            "After Effects Preset (*.ffx)")
        if not path: return
        self._do_export_ffx(path)

    def _do_export_ffx(self, path: str):
        """Write the FFX binary to path."""
        effect_name = self._effect_name.text().strip()
        match_name  = self._match_name.text().strip()
        if not effect_name or not match_name:
            QMessageBox.warning(self,"Export","Effect Name and Match Name are required.")
            return
        controls = self._flatten()
        if not controls:
            QMessageBox.warning(self,"Export","Add at least one control.")
            return
        try:
            full_match_name = f"Pseudo/{match_name}"
            generate_ffx_file(control_name=effect_name, match_name=full_match_name,
                              controls=controls, output_path=path)
            self.statusBar().showMessage(f"Exported: {path}")
        except Exception as e:
            QMessageBox.critical(self,"Export Error",str(e))

def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)

# ── entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))
    app.setStyle("fusion")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,     QColor(DARK_BG))
    pal.setColor(QPalette.ColorRole.Base,       QColor(ITEM_BG))
    pal.setColor(QPalette.ColorRole.Button,     QColor(BORDER))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Text,       QColor(TEXT))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    # app.setPalette(pal)

    app.setStyleSheet(SS)
    win = FFXBuilder()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()