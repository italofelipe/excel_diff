from __future__ import annotations

from pathlib import Path

import openpyxl
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.diff_engine import DiffResult, run_diff
from ...core.normalizer import NormConfig
from ..diff_table import DiffTable
from ..drop_zone import DropZone
from ..export_dialog import ExportDialog
from ..settings_dialog import SettingsDialog, load_settings, settings_to_norm_config
from ..side_by_side import SideBySideView
from ...export.writer import write_diff


class DiffWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, path_a, path_b, threshold, config, key_col_a='', key_col_b=''):
        super().__init__()
        self.path_a = path_a
        self.path_b = path_b
        self.threshold = threshold
        self.config = config
        self.key_col_a = key_col_a or None
        self.key_col_b = key_col_b or None

    def run(self):
        try:
            result = run_diff(
                self.path_a, self.path_b, self.threshold,
                key_col_a=self.key_col_a, key_col_b=self.key_col_b,
                config=self.config,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DiffTool(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: DiffResult | None = None
        self._settings = load_settings()
        self._worker: DiffWorker | None = None
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar strip
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName('diff_toolbar')
        toolbar_frame.setStyleSheet(
            '#diff_toolbar { background:#f5f5f5; border-bottom:1px solid #ddd; }'
        )
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        self._compare_btn = QPushButton('Comparar')
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._run_diff)
        toolbar_layout.addWidget(self._compare_btn)

        toolbar_layout.addWidget(_sep())
        settings_btn = QPushButton('Configuracoes')
        settings_btn.clicked.connect(self._open_settings)
        toolbar_layout.addWidget(settings_btn)

        toolbar_layout.addWidget(_sep())
        export_btn = QPushButton('Exportar...')
        export_btn.clicked.connect(self._export)
        toolbar_layout.addWidget(export_btn)

        toolbar_layout.addWidget(_sep())
        clear_btn = QPushButton('Limpar')
        clear_btn.clicked.connect(self._clear)
        toolbar_layout.addWidget(clear_btn)
        toolbar_layout.addStretch()
        main_layout.addWidget(toolbar_frame)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 4)
        content_layout.setSpacing(8)

        # Drop zones
        drop_row = QHBoxLayout()
        self._zone_a = DropZone('Arquivo A')
        self._zone_b = DropZone('Arquivo B')
        self._zone_a.file_dropped.connect(self._on_file_a)
        self._zone_b.file_dropped.connect(self._on_file_b)
        drop_row.addWidget(self._zone_a)
        drop_row.addWidget(self._zone_b)
        content_layout.addLayout(drop_row)

        # Tabs
        self._tabs = QTabWidget()
        self._diff_view = SideBySideView()
        self._table_only_a = DiffTable()
        self._table_only_b = DiffTable()
        self._table_matched = DiffTable()

        self._tabs.addTab(self._diff_view, 'Diff Visual')
        self._tabs.addTab(self._table_only_a, 'Apenas em A (0)')
        self._tabs.addTab(self._table_only_b, 'Apenas em B (0)')
        self._tabs.addTab(self._table_matched, 'Coincidencias (0)')
        content_layout.addWidget(self._tabs)

        for table in (self._table_only_a, self._table_only_b, self._table_matched):
            table.copy_to_b_requested.connect(self._copy_rows_to_b)
            table.copy_to_a_requested.connect(self._copy_rows_to_a)
        self._diff_view.copy_to_b_requested.connect(self._copy_rows_to_b)
        self._diff_view.copy_to_a_requested.connect(self._copy_rows_to_a)

        main_layout.addWidget(content)

        # Status bar
        self._status_label = QLabel('Selecione dois arquivos para comparar')
        self._status_label.setStyleSheet(
            'padding:4px 8px; background:#fafafa; border-top:1px solid #ddd;'
            ' color:#555; font-size:11px;'
        )
        main_layout.addWidget(self._status_label)

    def _on_file_a(self, _):
        self._update_compare_button()

    def _on_file_b(self, _):
        self._update_compare_button()

    def _update_compare_button(self):
        self._compare_btn.setEnabled(
            bool(self._zone_a.current_path and self._zone_b.current_path)
        )

    def _update_status(self, result: DiffResult | None = None):
        if result is None:
            self._status_label.setText('Selecione dois arquivos para comparar')
        else:
            self._status_label.setText(
                f'{result.file_a_name} vs {result.file_b_name}  |  '
                f'Threshold: {result.threshold}%  |  '
                f'Apenas em A: {len(result.only_in_a)}  |  '
                f'Apenas em B: {len(result.only_in_b)}  |  '
                f'Coincidencias: {len(result.matched)}'
            )

    def _run_diff(self):
        path_a = self._zone_a.current_path
        path_b = self._zone_b.current_path
        if not path_a or not path_b:
            return

        config = settings_to_norm_config(self._settings)
        threshold = float(self._settings.get('threshold', 75))

        self._progress = QProgressDialog('Comparando planilhas...', None, 0, 0, self)
        self._progress.setWindowTitle('Aguarde')
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.show()

        self._worker = DiffWorker(
            path_a, path_b, threshold, config,
            key_col_a=self._zone_a.selected_column,
            key_col_b=self._zone_b.selected_column,
        )
        self._worker.finished.connect(self._on_diff_done)
        self._worker.error.connect(self._on_diff_error)
        self._worker.start()

    def _on_diff_done(self, result: DiffResult):
        self._progress.close()
        self._result = result

        self._diff_view.populate(result)
        self._table_only_a.populate(result, 'only_a')
        self._table_only_b.populate(result, 'only_b')
        self._table_matched.populate(result, 'matched')

        self._tabs.setTabText(1, f'Apenas em A ({len(result.only_in_a)})')
        self._tabs.setTabText(2, f'Apenas em B ({len(result.only_in_b)})')
        self._tabs.setTabText(3, f'Coincidencias ({len(result.matched)})')
        self._tabs.setCurrentIndex(0)
        self._update_status(result)

    def _on_diff_error(self, message: str):
        self._progress.close()
        if 'Permission' in message:
            msg = 'Nao foi possivel abrir o arquivo. Esta aberto no Excel?'
        elif 'BadZipFile' in message or 'not a zip' in message.lower():
            msg = 'O arquivo nao e um .xlsx valido.'
        else:
            msg = f'Erro ao comparar arquivos:\n{message}'
        QMessageBox.critical(self, 'Erro', msg)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self._settings = dlg.get_settings()
            if self._result:
                self._run_diff()

    def _export(self):
        if self._result is None:
            QMessageBox.information(self, 'Exportar', 'Execute uma comparacao primeiro.')
            return
        dlg = ExportDialog(self._result.file_a_name, self._result.file_b_name, self)
        if dlg.exec():
            opts = dlg.get_options()
            try:
                write_diff(self._result, opts['output_path'], opts)
                QMessageBox.information(self, 'Exportado', f'Arquivo salvo em:\n{opts["output_path"]}')
            except Exception as e:
                QMessageBox.critical(self, 'Erro ao exportar', str(e))

    def _copy_rows_to_b(self, rows):
        self._copy_rows(rows, self._zone_b.current_path, 'B')

    def _copy_rows_to_a(self, rows):
        self._copy_rows(rows, self._zone_a.current_path, 'A')

    def _copy_rows(self, rows: list[dict], target_path: str, label: str):
        if not target_path:
            QMessageBox.warning(self, 'Erro', f'Arquivo {label} nao selecionado.')
            return
        confirm = QMessageBox.question(
            self, 'Confirmar copia',
            f'Adicionar {len(rows)} linha(s) ao Arquivo {label}?\n'
            f'({Path(target_path).name})\n\nEsta acao nao pode ser desfeita.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            wb = openpyxl.load_workbook(target_path)
            ws = wb.active
            for row_dict in rows:
                ws.append(list(row_dict.values()))
            wb.save(target_path)
            QMessageBox.information(
                self, 'Concluido',
                f'{len(rows)} linha(s) adicionada(s) ao Arquivo {label}.\n'
                'A comparacao sera atualizada.'
            )
            self._run_diff()
        except PermissionError:
            QMessageBox.critical(self, 'Erro', 'Nao foi possivel salvar. Arquivo aberto no Excel?')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', str(e))

    def _clear(self):
        self._zone_a.clear()
        self._zone_b.clear()
        self._result = None
        self._diff_view._table.clearContents()
        self._diff_view._table.setRowCount(0)
        self._diff_view._table.setColumnCount(0)
        for table in (self._table_only_a, self._table_only_b, self._table_matched):
            table.clearContents()
            table.setRowCount(0)
            table.setColumnCount(0)
        self._tabs.setTabText(1, 'Apenas em A (0)')
        self._tabs.setTabText(2, 'Apenas em B (0)')
        self._tabs.setTabText(3, 'Coincidencias (0)')
        self._update_compare_button()
        self._update_status()


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet('color: #ccc;')
    return f
