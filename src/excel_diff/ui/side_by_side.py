from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QScrollBar,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.diff_engine import DiffResult

# GitHub diff colour palette
_COLOR_REMOVED_CELL = QColor(255, 215, 213)   # red  — only in A
_COLOR_REMOVED_EMPTY = QColor(235, 235, 235)  # grey — empty B side of an A-only row
_COLOR_ADDED_CELL = QColor(204, 255, 213)     # green — only in B
_COLOR_ADDED_EMPTY = QColor(235, 235, 235)    # grey — empty A side of a B-only row
_COLOR_MATCH_HIGH = QColor(213, 240, 255)     # blue — matched ≥ 90 %
_COLOR_MATCH_LOW = QColor(255, 248, 197)      # amber — matched < 90 % (fuzzy)
_COLOR_HEADER_A = QColor(220, 100, 90)        # red-ish header tint for A side
_COLOR_HEADER_B = QColor(80, 160, 80)         # green-ish header tint for B side
_COLOR_SECTION = QColor(246, 248, 250)        # GitHub section divider bg


def _item(text: str, bg: QColor, bold: bool = False, align_center: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setBackground(QBrush(bg))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if bold:
        f = it.font()
        f.setBold(True)
        it.setFont(f)
    if align_center:
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


def _section_item(text: str, col_span_hint: int = 1) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setBackground(QBrush(_COLOR_SECTION))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    f = it.font()
    f.setBold(True)
    f.setItalic(True)
    it.setFont(f)
    it.setForeground(QBrush(QColor(100, 100, 100)))
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


class SideBySideView(QWidget):
    """GitHub-style side-by-side diff table."""

    copy_to_b_requested = pyqtSignal(list)
    copy_to_a_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: DiffResult | None = None
        # Maps table row index → (kind, original_row_index)
        # kind: 'matched', 'only_a', 'only_b'
        self._row_map: list[tuple[str, int]] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Legend bar
        legend = QHBoxLayout()
        legend.setContentsMargins(8, 4, 8, 4)
        for color, label in [
            (_COLOR_REMOVED_CELL, 'Apenas em A'),
            (_COLOR_ADDED_CELL, 'Apenas em B'),
            (_COLOR_MATCH_HIGH, 'Coincidencia exata (>=90%)'),
            (_COLOR_MATCH_LOW, 'Coincidencia aproximada (<90%)'),
        ]:
            dot = QLabel('  ')
            dot.setStyleSheet(
                f'background:{color.name()}; border:1px solid #ccc;'
                ' border-radius:3px; min-width:18px; max-width:18px;'
            )
            lbl = QLabel(label)
            lbl.setStyleSheet('color:#444; font-size:11px;')
            legend.addWidget(dot)
            legend.addWidget(lbl)
            legend.addSpacing(12)
        legend.addStretch()
        legend_widget = QWidget()
        legend_widget.setLayout(legend)
        legend_widget.setStyleSheet('background:#f8f8f8; border-bottom:1px solid #ddd;')
        layout.addWidget(legend_widget)

        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._table)

    def populate(self, result: DiffResult):
        self._result = result
        self._row_map = []
        self._table.clearContents()
        self._table.setRowCount(0)

        ha = result.headers_a
        hb = result.headers_b

        # Build column list: [A cols...] [separator] [B cols...]
        sep_col = len(ha)
        total_cols = len(ha) + 1 + len(hb)
        self._table.setColumnCount(total_cols)
        self._sep_col = sep_col

        # Headers
        all_headers = [f'{h}' for h in ha] + [''] + [f'{h}' for h in hb]
        self._table.setHorizontalHeaderLabels(all_headers)

        header = self._table.horizontalHeader()
        # Colour A-side header labels red, B-side green
        for col, h in enumerate(ha):
            item = QTableWidgetItem(h)
            item.setForeground(QBrush(QColor(180, 40, 30)))
            item.setFont(QFont('', -1, QFont.Weight.Bold))
            self._table.setHorizontalHeaderItem(col, item)
        for i, h in enumerate(hb):
            col = sep_col + 1 + i
            item = QTableWidgetItem(h)
            item.setForeground(QBrush(QColor(30, 130, 60)))
            item.setFont(QFont('', -1, QFont.Weight.Bold))
            self._table.setHorizontalHeaderItem(col, item)

        # Separator column: narrow, dark
        self._table.setColumnWidth(sep_col, 8)
        header.setSectionResizeMode(sep_col, QHeaderView.ResizeMode.Fixed)

        self._table.setRowCount(0)

        # ── Section: Matched ──────────────────────────────────────────────
        if result.matched:
            self._add_section_row(
                f'  ==  Coincidencias -- {len(result.matched)} par(es)',
                total_cols,
            )
            for i, pair in enumerate(result.matched):
                color = _COLOR_MATCH_HIGH if pair.score >= 90 else _COLOR_MATCH_LOW
                self._add_pair_row(pair.row_a, pair.row_b, ha, hb, color, sep_col)
                self._row_map.append(('matched', i))

        # ── Section: Only in A ────────────────────────────────────────────
        if result.only_in_a:
            self._add_section_row(
                f'  A  Apenas em {result.file_a_name} -- {len(result.only_in_a)} linha(s)',
                total_cols,
            )
            for i, row in enumerate(result.only_in_a):
                self._add_only_a_row(row, ha, hb, sep_col)
                self._row_map.append(('only_a', i))

        # ── Section: Only in B ────────────────────────────────────────────
        if result.only_in_b:
            self._add_section_row(
                f'  B  Apenas em {result.file_b_name} -- {len(result.only_in_b)} linha(s)',
                total_cols,
            )
            for i, row in enumerate(result.only_in_b):
                self._add_only_b_row(row, ha, hb, sep_col)
                self._row_map.append(('only_b', i))

        # Resize key columns to content
        for col in range(total_cols):
            if col != sep_col:
                self._table.resizeColumnToContents(col)
                w = self._table.columnWidth(col)
                self._table.setColumnWidth(col, min(max(w, 80), 280))

    # ── Row builders ──────────────────────────────────────────────────────

    def _add_section_row(self, label: str, total_cols: int):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setRowHeight(r, 22)
        self._row_map.append(('section', -1))
        for c in range(total_cols):
            if c == 0:
                self._table.setItem(r, c, _section_item(label))
            else:
                it = QTableWidgetItem('')
                it.setBackground(QBrush(_COLOR_SECTION))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, c, it)
        self._table.setSpan(r, 0, 1, total_cols)

    def _fill_side(self, row_idx: int, col_offset: int, headers: list[str],
                   row_dict: dict, color: QColor):
        for i, h in enumerate(headers):
            self._table.setItem(row_idx, col_offset + i, _item(str(row_dict.get(h, '')), color))

    def _fill_empty_side(self, row_idx: int, col_offset: int, count: int, color: QColor):
        for i in range(count):
            self._table.setItem(row_idx, col_offset + i, _item('', color))

    def _add_sep_cell(self, row_idx: int, sep_col: int, color: QColor):
        it = QTableWidgetItem('')
        it.setBackground(QBrush(QColor(160, 160, 160)))
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row_idx, sep_col, it)

    def _add_pair_row(self, row_a: dict, row_b: dict, ha: list[str], hb: list[str],
                      color: QColor, sep_col: int):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._fill_side(r, 0, ha, row_a, color)
        self._add_sep_cell(r, sep_col, color)
        self._fill_side(r, sep_col + 1, hb, row_b, color)

    def _add_only_a_row(self, row: dict, ha: list[str], hb: list[str], sep_col: int):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._fill_side(r, 0, ha, row, _COLOR_REMOVED_CELL)
        self._add_sep_cell(r, sep_col, _COLOR_REMOVED_CELL)
        self._fill_empty_side(r, sep_col + 1, len(hb), _COLOR_REMOVED_EMPTY)

    def _add_only_b_row(self, row: dict, ha: list[str], hb: list[str], sep_col: int):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._fill_empty_side(r, 0, len(ha), _COLOR_ADDED_EMPTY)
        self._add_sep_cell(r, sep_col, _COLOR_ADDED_CELL)
        self._fill_side(r, sep_col + 1, hb, row, _COLOR_ADDED_CELL)

    # ── Context menu ──────────────────────────────────────────────────────

    def _show_context_menu(self, pos):
        if not self._result:
            return
        selected = {item.row() for item in self._table.selectedItems()}
        if not selected:
            return

        # Collect actionable rows (skip section dividers)
        only_a_rows, only_b_rows = [], []
        for table_row in selected:
            if table_row >= len(self._row_map):
                continue
            kind, idx = self._row_map[table_row]
            if kind == 'only_a':
                only_a_rows.append(self._result.only_in_a[idx])
            elif kind == 'only_b':
                only_b_rows.append(self._result.only_in_b[idx])

        menu = QMenu(self)
        if only_a_rows:
            act = menu.addAction(f'Copiar {len(only_a_rows)} linha(s) → Arquivo B')
            act.triggered.connect(lambda: self.copy_to_b_requested.emit(only_a_rows))
        if only_b_rows:
            act = menu.addAction(f'Copiar {len(only_b_rows)} linha(s) → Arquivo A')
            act.triggered.connect(lambda: self.copy_to_a_requested.emit(only_b_rows))

        if menu.actions():
            menu.exec(self._table.viewport().mapToGlobal(pos))
