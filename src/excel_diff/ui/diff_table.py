from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
)

from ..core.diff_engine import DiffResult

COLOR_ONLY_A = QColor(255, 210, 210)
COLOR_ONLY_B = QColor(210, 230, 255)
COLOR_MATCHED = QColor(210, 245, 210)
COLOR_HEADER = QColor(240, 240, 240)


class DiffTable(QTableWidget):
    copy_to_b_requested = pyqtSignal(list)
    copy_to_a_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: DiffResult | None = None
        self._view = 'all'
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def populate(self, result: DiffResult, view: str = 'all'):
        self._result = result
        self._view = view
        self.clearContents()
        self.setRowCount(0)

        if view == 'only_a':
            self._fill_single(result.only_in_a, result.headers_a, COLOR_ONLY_A)
        elif view == 'only_b':
            self._fill_single(result.only_in_b, result.headers_b, COLOR_ONLY_B)
        elif view == 'matched':
            self._fill_matched(result)
        else:
            self._fill_all(result)

    def _fill_single(self, rows: list[dict], headers: list[str], color: QColor):
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        for row_dict in rows:
            row_idx = self.rowCount()
            self.insertRow(row_idx)
            for col_idx, header in enumerate(headers):
                item = QTableWidgetItem(str(row_dict.get(header, '')))
                item.setBackground(QBrush(color))
                self.setItem(row_idx, col_idx, item)

    def _fill_matched(self, result: DiffResult):
        headers_a = [f'A: {h}' for h in result.headers_a]
        headers_b = [f'B: {h}' for h in result.headers_b]
        headers = headers_a + headers_b + ['Similaridade %']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        for pair in result.matched:
            row_idx = self.rowCount()
            self.insertRow(row_idx)
            for col_idx, header in enumerate(result.headers_a):
                item = QTableWidgetItem(str(pair.row_a.get(header, '')))
                item.setBackground(QBrush(COLOR_MATCHED))
                self.setItem(row_idx, col_idx, item)
            offset = len(result.headers_a)
            for col_idx, header in enumerate(result.headers_b):
                item = QTableWidgetItem(str(pair.row_b.get(header, '')))
                item.setBackground(QBrush(COLOR_MATCHED))
                self.setItem(row_idx, offset + col_idx, item)
            score_item = QTableWidgetItem(f'{pair.score:.0f}%')
            score_item.setBackground(QBrush(COLOR_MATCHED))
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, len(headers) - 1, score_item)

    def _fill_all(self, result: DiffResult):
        all_headers = list(dict.fromkeys(result.headers_a + result.headers_b))
        status_col = 'Status'
        self.setColumnCount(len(all_headers) + 1)
        self.setHorizontalHeaderLabels([status_col] + all_headers)

        def add_rows(rows, color, status):
            for row_dict in rows:
                row_idx = self.rowCount()
                self.insertRow(row_idx)
                status_item = QTableWidgetItem(status)
                status_item.setBackground(QBrush(color))
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, 0, status_item)
                for col_idx, header in enumerate(all_headers):
                    item = QTableWidgetItem(str(row_dict.get(header, '')))
                    item.setBackground(QBrush(color))
                    self.setItem(row_idx, col_idx + 1, item)

        add_rows(result.only_in_a, COLOR_ONLY_A, f'Apenas em {result.file_a_name}')
        add_rows(result.only_in_b, COLOR_ONLY_B, f'Apenas em {result.file_b_name}')
        for pair in result.matched:
            row_dict = {**pair.row_b, **pair.row_a}
            row_idx = self.rowCount()
            self.insertRow(row_idx)
            status_item = QTableWidgetItem(f'Coincidência {pair.score:.0f}%')
            status_item.setBackground(QBrush(COLOR_MATCHED))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row_idx, 0, status_item)
            for col_idx, header in enumerate(all_headers):
                item = QTableWidgetItem(str(row_dict.get(header, '')))
                item.setBackground(QBrush(COLOR_MATCHED))
                self.setItem(row_idx, col_idx + 1, item)

    def _show_context_menu(self, pos):
        if self._result is None:
            return
        selected = self.selectedItems()
        if not selected:
            return
        selected_rows = list({item.row() for item in selected})

        menu = QMenu(self)
        if self._view == 'only_a':
            action = menu.addAction(f'Copiar {len(selected_rows)} linha(s) para Arquivo B')
            action.triggered.connect(lambda: self._emit_copy_to_b(selected_rows))
        elif self._view == 'only_b':
            action = menu.addAction(f'Copiar {len(selected_rows)} linha(s) para Arquivo A')
            action.triggered.connect(lambda: self._emit_copy_to_a(selected_rows))

        if menu.actions():
            menu.exec(self.viewport().mapToGlobal(pos))

    def _emit_copy_to_b(self, row_indices: list[int]):
        if self._result is None:
            return
        rows = [self._result.only_in_a[i] for i in row_indices if i < len(self._result.only_in_a)]
        self.copy_to_b_requested.emit(rows)

    def _emit_copy_to_a(self, row_indices: list[int]):
        if self._result is None:
            return
        rows = [self._result.only_in_b[i] for i in row_indices if i < len(self._result.only_in_b)]
        self.copy_to_a_requested.emit(rows)
