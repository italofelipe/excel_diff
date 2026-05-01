from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(self, file_a_name: str, file_b_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Exportar resultado')
        self.setMinimumWidth(420)
        self._output_path = ''
        self._build_ui(file_a_name, file_b_name)

    def _build_ui(self, file_a_name: str, file_b_name: str):
        layout = QVBoxLayout(self)

        sheets_group = QGroupBox('Abas a incluir no arquivo exportado')
        sheets_layout = QVBoxLayout(sheets_group)
        self._cb_only_a = QCheckBox(f'Apenas em {file_a_name} (vermelho)')
        self._cb_only_b = QCheckBox(f'Apenas em {file_b_name} (azul)')
        self._cb_matched = QCheckBox('Coincidências (verde)')
        self._cb_summary = QCheckBox('Resumo')
        for cb in (self._cb_only_a, self._cb_only_b, self._cb_matched, self._cb_summary):
            cb.setChecked(True)
            sheets_layout.addWidget(cb)
        layout.addWidget(sheets_group)

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText('Caminho do arquivo de saída...')
        browse_btn = QPushButton('Procurar...')
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Salvar resultado como', '', 'Planilhas Excel (*.xlsx)'
        )
        if path:
            if not path.lower().endswith('.xlsx'):
                path += '.xlsx'
            self._path_edit.setText(path)

    def _accept(self):
        if not self._path_edit.text().strip():
            return
        self._output_path = self._path_edit.text().strip()
        self.accept()

    def get_options(self) -> dict:
        return {
            'output_path': self._output_path,
            'only_a': self._cb_only_a.isChecked(),
            'only_b': self._cb_only_b.isChecked(),
            'matched': self._cb_matched.isChecked(),
            'summary': self._cb_summary.isChecked(),
        }
