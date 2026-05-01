from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.splitter import (
    ColumnSplitCandidate,
    SplitConfig,
    SplitResult,
    detect_split_candidates,
    run_split,
    write_split,
    _apply_split_to_rows,
)
from ...core.loader import load_file
from ..drop_zone import DropZone


class SplitWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, path, config):
        super().__init__()
        self.path = path
        self.config = config

    def run(self):
        try:
            result = run_split(self.path, self.config)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _CandidatesTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['Coluna', 'Delimitador', 'Partes', 'Nomes propostos'])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self._candidates: list[ColumnSplitCandidate] = []

    def load_candidates(self, candidates: list[ColumnSplitCandidate]):
        self._candidates = list(candidates)
        self.setRowCount(len(candidates))
        for i, c in enumerate(candidates):
            chk = QCheckBox()
            chk.setChecked(c.enabled)
            chk.stateChanged.connect(lambda state, idx=i: self._toggle(idx, state))
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.setCellWidget(i, 0, chk_widget)

            delim_display = 'ponto-e-vírgula (;)' if c.delimiter == ';' else 'vírgula (,)'
            self.setItem(i, 1, QTableWidgetItem(delim_display))
            self.setItem(i, 2, QTableWidgetItem(str(c.max_parts)))

            names_edit = QLineEdit(', '.join(c.proposed_names))
            names_edit.setFrame(False)
            names_edit.setPlaceholderText('nome_1, nome_2, ...')
            names_edit.textChanged.connect(lambda text, idx=i: self._update_names(idx, text))
            self.setCellWidget(i, 3, names_edit)

            col_label = QLabel(f' {c.column} ({int(c.confidence * 100)}%)')
            col_label.setStyleSheet('font-weight:bold;')
            self.setItem(i, 0, QTableWidgetItem(f'{c.column} ({int(c.confidence * 100)}%)'))

        self.setColumnHidden(0, False)
        self._rebuild_col0_checkboxes()

    def _rebuild_col0_checkboxes(self):
        for i, c in enumerate(self._candidates):
            chk = QCheckBox(f'{c.column} ({int(c.confidence * 100)}%)')
            chk.setChecked(c.enabled)
            chk.stateChanged.connect(lambda state, idx=i: self._toggle(idx, state))
            self.setCellWidget(i, 0, chk)

    def _toggle(self, row: int, state: int):
        if row < len(self._candidates):
            self._candidates[row].enabled = bool(state)

    def _update_names(self, row: int, text: str):
        if row < len(self._candidates):
            names = [n.strip() for n in text.split(',') if n.strip()]
            self._candidates[row].proposed_names = names

    def get_candidates(self) -> list[ColumnSplitCandidate]:
        result = []
        for i, c in enumerate(self._candidates):
            names_widget = self.cellWidget(i, 3)
            if names_widget:
                names = [n.strip() for n in names_widget.text().split(',') if n.strip()]
                if names:
                    c.proposed_names = names
            result.append(c)
        return result


class _PreviewTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def show_preview(self, headers: list[str], rows: list[dict]):
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        preview_rows = rows[:5]
        self.setRowCount(len(preview_rows))
        for r, row in enumerate(preview_rows):
            for c, h in enumerate(headers):
                self.setItem(r, c, QTableWidgetItem(str(row.get(h, ''))))


class SplitterTool(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers: list[str] = []
        self._rows: list[dict] = []
        self._result: SplitResult | None = None
        self._worker: SplitWorker | None = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName('splitter_toolbar')
        toolbar_frame.setStyleSheet(
            '#splitter_toolbar { background:#f5f5f5; border-bottom:1px solid #ddd; }'
        )
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        self._split_btn = QPushButton('Separar colunas')
        self._split_btn.setEnabled(False)
        self._split_btn.clicked.connect(self._run_split)
        toolbar_layout.addWidget(self._split_btn)

        toolbar_layout.addWidget(_sep())
        self._export_btn = QPushButton('Exportar...')
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        toolbar_layout.addWidget(self._export_btn)

        toolbar_layout.addWidget(_sep())
        clear_btn = QPushButton('Limpar')
        clear_btn.clicked.connect(self._clear)
        toolbar_layout.addWidget(clear_btn)
        toolbar_layout.addStretch()
        main_layout.addWidget(toolbar_frame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 4)
        content_layout.setSpacing(8)

        self._zone = DropZone('Arquivo')
        self._zone.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._zone.file_dropped.connect(self._on_file_loaded)
        content_layout.addWidget(self._zone)

        candidates_label = QLabel('Colunas detectadas para separacao (marque as que deseja processar):')
        candidates_label.setStyleSheet('font-weight:bold; color:#333;')
        content_layout.addWidget(candidates_label)

        self._candidates_table = _CandidatesTable()
        self._candidates_table.setMaximumHeight(160)
        self._candidates_table.itemSelectionChanged.connect(self._refresh_preview)
        content_layout.addWidget(self._candidates_table)

        preview_label = QLabel('Pre-visualizacao (primeiras 5 linhas apos separacao):')
        preview_label.setStyleSheet('font-weight:bold; color:#333;')
        content_layout.addWidget(preview_label)

        self._preview_table = _PreviewTable()
        content_layout.addWidget(self._preview_table)

        main_layout.addWidget(content)

        self._status_label = QLabel('Selecione um arquivo para detectar colunas a separar')
        self._status_label.setStyleSheet(
            'padding:4px 8px; background:#fafafa; border-top:1px solid #ddd;'
            ' color:#555; font-size:11px;'
        )
        main_layout.addWidget(self._status_label)

    def _on_file_loaded(self, path: str):
        try:
            headers, rows = load_file(path)
            self._headers = headers
            self._rows = rows
            candidates = detect_split_candidates(headers, rows)
            self._candidates_table.load_candidates(candidates)
            if candidates:
                self._split_btn.setEnabled(True)
                self._status_label.setText(
                    f'{Path(path).name}  |  {len(headers)} colunas  |  '
                    f'{len(rows)} linhas  |  '
                    f'{len(candidates)} coluna(s) detectada(s) para separacao'
                )
                self._refresh_preview()
            else:
                self._split_btn.setEnabled(False)
                self._status_label.setText(
                    f'{Path(path).name}  |  {len(headers)} colunas  |  '
                    f'{len(rows)} linhas  |  '
                    'Nenhuma coluna detectada para separacao'
                )
        except Exception as e:
            self._status_label.setText(f'Erro ao carregar arquivo: {e}')

    def _refresh_preview(self):
        if not self._headers:
            return
        candidates = self._candidates_table.get_candidates()
        config = SplitConfig(candidates=candidates, drop_original=True)
        try:
            new_headers, new_rows = _apply_split_to_rows(self._headers, self._rows, config)
            self._preview_table.show_preview(new_headers, new_rows)
        except Exception:
            pass

    def _run_split(self):
        path = self._zone.current_path
        if not path:
            return

        candidates = self._candidates_table.get_candidates()
        enabled = [c for c in candidates if c.enabled]
        if not enabled:
            QMessageBox.warning(self, 'Aviso', 'Nenhuma coluna selecionada para separar.')
            return

        config = SplitConfig(candidates=candidates, drop_original=True)

        self._progress = QProgressDialog('Separando colunas...', None, 0, 0, self)
        self._progress.setWindowTitle('Aguarde')
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.show()

        self._worker = SplitWorker(path, config)
        self._worker.finished.connect(self._on_split_done)
        self._worker.error.connect(self._on_split_error)
        self._worker.start()

    def _on_split_done(self, result: SplitResult):
        self._progress.close()
        self._result = result
        self._export_btn.setEnabled(True)
        self._status_label.setText(
            f'{result.source_file}  |  '
            f'{len(result.headers)} colunas no resultado  |  '
            f'Colunas separadas: {", ".join(result.applied_columns)}'
        )
        QMessageBox.information(
            self, 'Concluido',
            f'Separacao concluida!\n\n'
            f'Colunas separadas: {", ".join(result.applied_columns)}\n'
            f'Total de colunas no resultado: {len(result.headers)}\n\n'
            'Clique em "Exportar..." para salvar.'
        )

    def _on_split_error(self, message: str):
        self._progress.close()
        QMessageBox.critical(self, 'Erro', f'Erro ao separar colunas:\n{message}')

    def _export(self):
        if self._result is None:
            return
        default_name = Path(self._zone.current_path).stem + '_separado.xlsx'
        path, _ = QFileDialog.getSaveFileName(
            self, 'Salvar resultado', default_name, 'Excel (*.xlsx)'
        )
        if not path:
            return
        try:
            write_split(self._result, path)
            QMessageBox.information(self, 'Exportado', f'Arquivo salvo em:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro ao exportar', str(e))

    def _clear(self):
        self._zone.clear()
        self._headers = []
        self._rows = []
        self._result = None
        self._candidates_table.setRowCount(0)
        self._preview_table.setRowCount(0)
        self._preview_table.setColumnCount(0)
        self._split_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._status_label.setText('Selecione um arquivo para detectar colunas a separar')


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet('color: #ccc;')
    return f
