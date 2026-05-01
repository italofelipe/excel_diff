from __future__ import annotations

from pathlib import Path

import openpyxl
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.diff_engine import DiffResult, run_diff
from ..core.normalizer import NormConfig
from .diff_table import DiffTable
from .drop_zone import DropZone
from .export_dialog import ExportDialog
from .settings_dialog import SettingsDialog, load_settings, settings_to_norm_config
from .side_by_side import SideBySideView
from ..export.writer import write_diff


class DiffWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        path_a: str,
        path_b: str,
        threshold: float,
        config: NormConfig,
        key_col_a: str = '',
        key_col_b: str = '',
    ):
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
                key_col_a=self.key_col_a,
                key_col_b=self.key_col_b,
                config=self.config,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Excel Diff — Comparador de Planilhas')
        self.setMinimumSize(900, 600)
        self._result: DiffResult | None = None
        self._settings = load_settings()
        self._worker: DiffWorker | None = None
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._compare_btn = QPushButton('▶  Comparar')
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._run_diff)
        toolbar.addWidget(self._compare_btn)

        toolbar.addSeparator()
        settings_btn = QPushButton('⚙  Configurações')
        settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(settings_btn)

        toolbar.addSeparator()
        export_btn = QPushButton('💾  Exportar...')
        export_btn.clicked.connect(self._export)
        toolbar.addWidget(export_btn)

        toolbar.addSeparator()
        clear_btn = QPushButton('✕  Limpar')
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        # Drop zones
        drop_row = QHBoxLayout()
        self._zone_a = DropZone('Arquivo A')
        self._zone_b = DropZone('Arquivo B')
        self._zone_a.file_dropped.connect(self._on_file_a)
        self._zone_b.file_dropped.connect(self._on_file_b)
        drop_row.addWidget(self._zone_a)
        drop_row.addWidget(self._zone_b)
        main_layout.addLayout(drop_row)

        # Tabs with diff tables
        self._tabs = QTabWidget()

        self._diff_view = SideBySideView()
        self._table_only_a = DiffTable()
        self._table_only_b = DiffTable()
        self._table_matched = DiffTable()

        self._tabs.addTab(self._diff_view, 'Diff Visual')
        self._tabs.addTab(self._table_only_a, 'Apenas em A (0)')
        self._tabs.addTab(self._table_only_b, 'Apenas em B (0)')
        self._tabs.addTab(self._table_matched, 'Coincidências (0)')
        main_layout.addWidget(self._tabs)

        self._diff_view.copy_to_b_requested.connect(self._copy_rows_to_b)
        self._diff_view.copy_to_a_requested.connect(self._copy_rows_to_a)
        for table in (self._table_only_a, self._table_only_b, self._table_matched):
            table.copy_to_b_requested.connect(self._copy_rows_to_b)
            table.copy_to_a_requested.connect(self._copy_rows_to_a)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel('Selecione dois arquivos .xlsx para comparar')
        self._status_bar.addWidget(self._status_label)

    def _on_file_a(self, path: str):
        self._update_compare_button()

    def _on_file_b(self, path: str):
        self._update_compare_button()

    def _update_compare_button(self):
        has_both = bool(self._zone_a.current_path and self._zone_b.current_path)
        self._compare_btn.setEnabled(has_both)

    def _update_status(self, result: DiffResult | None = None):
        if result is None:
            self._status_label.setText('Selecione dois arquivos .xlsx para comparar')
        else:
            threshold = result.threshold
            msg = (
                f'{result.file_a_name} vs {result.file_b_name}  |  '
                f'Threshold: {threshold}%  |  '
                f'Apenas em A: {len(result.only_in_a)}  |  '
                f'Apenas em B: {len(result.only_in_b)}  |  '
                f'Coincidências: {len(result.matched)}'
            )
            self._status_label.setText(msg)

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
        self._tabs.setTabText(3, f'Coincidências ({len(result.matched)})')
        self._tabs.setCurrentIndex(0)  # sempre abre no Diff Visual

        self._update_status(result)

    def _on_diff_error(self, message: str):
        self._progress.close()
        if 'Permission' in message or 'PermissionError' in message:
            msg = 'Não foi possível abrir o arquivo. Verifique se ele não está aberto no Excel.'
        elif 'BadZipFile' in message or 'not a zip' in message.lower():
            msg = 'O arquivo não é um .xlsx válido.'
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
            QMessageBox.information(self, 'Exportar', 'Execute uma comparação primeiro.')
            return
        dlg = ExportDialog(self._result.file_a_name, self._result.file_b_name, self)
        if dlg.exec():
            opts = dlg.get_options()
            try:
                write_diff(self._result, opts['output_path'], opts)
                QMessageBox.information(
                    self, 'Exportado', f'Arquivo salvo em:\n{opts["output_path"]}'
                )
            except Exception as e:
                QMessageBox.critical(self, 'Erro ao exportar', str(e))

    def _copy_rows_to_b(self, rows: list[dict]):
        self._copy_rows(rows, self._zone_b.current_path, 'B')

    def _copy_rows_to_a(self, rows: list[dict]):
        self._copy_rows(rows, self._zone_a.current_path, 'A')

    def _copy_rows(self, rows: list[dict], target_path: str, label: str):
        if not target_path:
            QMessageBox.warning(self, 'Erro', f'Arquivo {label} não selecionado.')
            return
        if not rows:
            return

        confirm = QMessageBox.question(
            self,
            'Confirmar cópia',
            f'Adicionar {len(rows)} linha(s) ao Arquivo {label}?\n'
            f'({Path(target_path).name})\n\n'
            'Esta ação não pode ser desfeita.',
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
                self, 'Concluído',
                f'{len(rows)} linha(s) adicionada(s) ao Arquivo {label}.\n'
                'A comparação será atualizada.'
            )
            self._run_diff()
        except PermissionError:
            QMessageBox.critical(
                self, 'Erro',
                'Não foi possível salvar. O arquivo está aberto no Excel?'
            )
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
        self._tabs.setTabText(3, 'Coincidências (0)')
        self._update_compare_button()
        self._update_status()
