from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.loader import detect_key_column, load_file

_ACCEPTED_EXTS = {'.xlsx', '.csv'}
_FILE_FILTER = 'Planilhas e CSV (*.xlsx *.csv);;Excel (*.xlsx);;CSV (*.csv)'


class _ColumnPickerDialog(QDialog):
    def __init__(self, headers: list[str], current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Selecionar coluna de produto')
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Qual coluna contém o nome do produto?'))
        self._combo = QComboBox()
        self._combo.addItems(headers)
        if current in headers:
            self._combo.setCurrentIndex(headers.index(current))
        layout.addWidget(self._combo)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected(self) -> str:
        return self._combo.currentText()


class DropZone(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._filename = ''
        self._headers: list[str] = []
        self._selected_col = ''
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel(self._label_text)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = title.font(); f.setBold(True); f.setPointSize(10); title.setFont(f)
        layout.addWidget(title)

        self._drop_label = QLabel('Arraste um arquivo .xlsx ou .csv\nou clique no botão abaixo')
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setWordWrap(True)
        self._drop_label.setStyleSheet(
            'border:2px dashed #aaa; border-radius:8px; padding:20px; color:#555;'
        )
        self._drop_label.setMinimumHeight(80)
        layout.addWidget(self._drop_label)

        btn = QPushButton('Selecionar arquivo...')
        btn.clicked.connect(self._open_dialog)
        layout.addWidget(btn)

        # Compact column info row — hidden until a file is loaded
        self._col_row = QHBoxLayout()
        self._col_info = QLabel('')
        self._col_info.setStyleSheet('color:#555; font-size:11px;')
        self._change_btn = QPushButton('alterar')
        self._change_btn.setFlat(True)
        self._change_btn.setStyleSheet(
            'color:#1565c0; font-size:11px; text-decoration:underline;'
            ' border:none; padding:0; margin:0;'
        )
        self._change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._change_btn.clicked.connect(self._open_column_picker)
        self._col_row.addWidget(self._col_info)
        self._col_row.addWidget(self._change_btn)
        self._col_row.addStretch()
        col_widget = QWidget()
        col_widget.setLayout(self._col_row)
        col_widget.hide()
        self._col_widget = col_widget
        layout.addWidget(col_widget)

    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f'Selecionar {self._label_text}', '', _FILE_FILTER
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._filename = path
        name = Path(path).name
        self._drop_label.setText(f'✓ {name}')
        self._drop_label.setStyleSheet(
            'border:2px solid #4caf50; border-radius:8px; padding:20px;'
            ' color:#2e7d32; background:#f1f8f1;'
        )
        self._load_columns(path)
        self.file_dropped.emit(path)

    def _load_columns(self, path: str):
        try:
            headers, _ = load_file(path)
        except Exception:
            headers = []
        self._headers = headers
        if headers:
            self._selected_col = detect_key_column(headers)
            self._update_col_label()
            self._col_widget.show()
        else:
            self._selected_col = ''
            self._col_widget.hide()

    def _update_col_label(self):
        self._col_info.setText(f'Coluna de produto:  {self._selected_col}')

    def _open_column_picker(self):
        if not self._headers:
            return
        dlg = _ColumnPickerDialog(self._headers, self._selected_col, self)
        if dlg.exec():
            self._selected_col = dlg.selected()
            self._update_col_label()

    def clear(self):
        self._filename = ''
        self._headers = []
        self._selected_col = ''
        self._drop_label.setText('Arraste um arquivo .xlsx ou .csv\nou clique no botão abaixo')
        self._drop_label.setStyleSheet(
            'border:2px dashed #aaa; border-radius:8px; padding:20px; color:#555;'
        )
        self._col_widget.hide()

    @property
    def current_path(self) -> str:
        return self._filename

    @property
    def selected_column(self) -> str:
        return self._selected_col

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            if any(Path(u.toLocalFile()).suffix.lower() in _ACCEPTED_EXTS
                   for u in event.mimeData().urls()):
                event.acceptProposedAction()
                self._drop_label.setStyleSheet(
                    'border:2px dashed #2196f3; border-radius:8px; padding:20px;'
                    ' color:#1565c0; background:#e3f2fd;'
                )
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        if not self._filename:
            self._drop_label.setStyleSheet(
                'border:2px dashed #aaa; border-radius:8px; padding:20px; color:#555;'
            )

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in _ACCEPTED_EXTS:
                self._set_file(path)
                event.acceptProposedAction()
                return
        event.ignore()
