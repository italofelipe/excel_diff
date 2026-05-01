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

from ...core.merger import (
    ColumnMapping,
    MergeConfig,
    MergeResult,
    detect_column_mappings,
    run_merge,
    write_merge,
)
from ...core.loader import load_file
from ..drop_zone import DropZone


class MergeWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, path_a, path_b, config):
        super().__init__()
        self.path_a = path_a
        self.path_b = path_b
        self.config = config

    def run(self):
        try:
            result = run_merge(self.path_a, self.path_b, self.config)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _MappingTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Coluna em A', 'Coluna em B', 'Nome no resultado'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)

    def load_mappings(self, mappings: list[ColumnMapping]):
        self.setRowCount(len(mappings))
        for i, m in enumerate(mappings):
            self.setItem(i, 0, QTableWidgetItem(m.col_a or '—'))
            self.setItem(i, 1, QTableWidgetItem(m.col_b or '—'))
            name_edit = QLineEdit(m.output_name)
            name_edit.setFrame(False)
            name_edit.textChanged.connect(lambda text, idx=i: self._update_name(idx, text))
            self.setCellWidget(i, 2, name_edit)
        self._mappings = list(mappings)

    def _update_name(self, row: int, text: str):
        if row < len(self._mappings):
            self._mappings[row].output_name = text

    def get_mappings(self) -> list[ColumnMapping]:
        mappings = []
        for i, m in enumerate(self._mappings):
            widget = self.cellWidget(i, 2)
            name = widget.text().strip() if widget else m.output_name
            mappings.append(ColumnMapping(col_a=m.col_a, col_b=m.col_b, output_name=name or m.output_name))
        return mappings


class MergeTool(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: MergeResult | None = None
        self._mappings: list[ColumnMapping] = []
        self._worker: MergeWorker | None = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar_frame = QFrame()
        toolbar_frame.setObjectName('merge_toolbar')
        toolbar_frame.setStyleSheet(
            '#merge_toolbar { background:#f5f5f5; border-bottom:1px solid #ddd; }'
        )
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        self._merge_btn = QPushButton('Mesclar')
        self._merge_btn.setEnabled(False)
        self._merge_btn.clicked.connect(self._run_merge)
        toolbar_layout.addWidget(self._merge_btn)

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

        drop_row = QHBoxLayout()
        self._zone_a = DropZone('Arquivo A')
        self._zone_b = DropZone('Arquivo B')
        self._zone_a.file_dropped.connect(self._on_file_changed)
        self._zone_b.file_dropped.connect(self._on_file_changed)
        drop_row.addWidget(self._zone_a)
        drop_row.addWidget(self._zone_b)
        content_layout.addLayout(drop_row)

        options_row = QHBoxLayout()
        self._dedup_check = QCheckBox('Remover duplicatas')
        options_row.addWidget(self._dedup_check)
        options_row.addWidget(QLabel('Coluna-chave para dedup:'))
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText('Nome da coluna (opcional)')
        self._key_edit.setMaximumWidth(200)
        options_row.addWidget(self._key_edit)
        options_row.addStretch()
        content_layout.addLayout(options_row)

        mapping_label = QLabel('Mapeamento de colunas (edite o nome do resultado se quiser):')
        mapping_label.setStyleSheet('font-weight:bold; color:#333;')
        content_layout.addWidget(mapping_label)

        self._mapping_table = _MappingTable()
        content_layout.addWidget(self._mapping_table)

        main_layout.addWidget(content)

        self._status_label = QLabel('Selecione dois arquivos para mesclar')
        self._status_label.setStyleSheet(
            'padding:4px 8px; background:#fafafa; border-top:1px solid #ddd;'
            ' color:#555; font-size:11px;'
        )
        main_layout.addWidget(self._status_label)

    def _on_file_changed(self, _):
        path_a = self._zone_a.current_path
        path_b = self._zone_b.current_path
        self._merge_btn.setEnabled(bool(path_a and path_b))
        if path_a and path_b:
            try:
                headers_a, _ = load_file(path_a)
                headers_b, _ = load_file(path_b)
                self._mappings = detect_column_mappings(headers_a, headers_b)
                self._mapping_table.load_mappings(self._mappings)
                self._status_label.setText(
                    f'A: {Path(path_a).name} ({len(headers_a)} colunas)  |  '
                    f'B: {Path(path_b).name} ({len(headers_b)} colunas)'
                )
            except Exception as e:
                self._status_label.setText(f'Erro ao carregar colunas: {e}')

    def _run_merge(self):
        path_a = self._zone_a.current_path
        path_b = self._zone_b.current_path
        if not path_a or not path_b:
            return

        mappings = self._mapping_table.get_mappings()
        config = MergeConfig(
            mappings=mappings,
            remove_duplicates=self._dedup_check.isChecked(),
            key_column=self._key_edit.text().strip(),
        )

        self._progress = QProgressDialog('Mesclando arquivos...', None, 0, 0, self)
        self._progress.setWindowTitle('Aguarde')
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.show()

        self._worker = MergeWorker(path_a, path_b, config)
        self._worker.finished.connect(self._on_merge_done)
        self._worker.error.connect(self._on_merge_error)
        self._worker.start()

    def _on_merge_done(self, result: MergeResult):
        self._progress.close()
        self._result = result
        self._export_btn.setEnabled(True)
        total = len(result.rows)
        self._status_label.setText(
            f'{result.source_a} + {result.source_b}  |  '
            f'Linhas de A: {result.rows_from_a}  |  '
            f'Linhas de B: {result.rows_from_b}  |  '
            f'Total: {total}'
        )
        QMessageBox.information(
            self, 'Concluido',
            f'Mesclagem concluida!\n\n'
            f'Linhas de A: {result.rows_from_a}\n'
            f'Linhas de B: {result.rows_from_b}\n'
            f'Total: {total}\n\n'
            'Clique em "Exportar..." para salvar o resultado.'
        )

    def _on_merge_error(self, message: str):
        self._progress.close()
        QMessageBox.critical(self, 'Erro', f'Erro ao mesclar arquivos:\n{message}')

    def _export(self):
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Salvar resultado', 'mesclado.xlsx', 'Excel (*.xlsx)'
        )
        if not path:
            return
        try:
            write_merge(self._result, path)
            QMessageBox.information(self, 'Exportado', f'Arquivo salvo em:\n{path}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro ao exportar', str(e))

    def _clear(self):
        self._zone_a.clear()
        self._zone_b.clear()
        self._result = None
        self._mappings = []
        self._mapping_table.setRowCount(0)
        self._export_btn.setEnabled(False)
        self._merge_btn.setEnabled(False)
        self._dedup_check.setChecked(False)
        self._key_edit.clear()
        self._status_label.setText('Selecione dois arquivos para mesclar')


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet('color: #ccc;')
    return f
