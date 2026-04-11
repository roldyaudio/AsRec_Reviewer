import os

from lib_installer import (
    ensure_pip,
    install_pytorch_cuda_forced,
    install_requirements_in_directory,
)

ensure_pip()
install_pytorch_cuda_forced()
install_requirements_in_directory("C:/Apps/AsRec_Reviewer")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QPushButton, QWidget,
    QVBoxLayout, QGridLayout, QLineEdit, QFileDialog, QComboBox, QInputDialog
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt

# Import your existing logic
import transcribe_or_compare as core

def center_app(app_window, app_width: int, app_height: int):
    """Centers the window to the main display/monitor using PySide6"""
    app_window.resize(app_width, app_height)
    screen = QGuiApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()
    
    # Tu lógica: Centro en X, 1/5 de la pantalla en Y
    x = int((screen_geometry.width() / 2.5) - (app_width / 1))
    y = int((screen_geometry.height() / 2) - (app_height / 2))
    
    app_window.move(screen_geometry.x() + x , screen_geometry.y() + y)

class MainWindow(QMainWindow):
    ENGINE_MODELS = {
        "whisper": ["Tiny", "Base", "Small", "Medium", "Large", "Large-v3"],
        "deepgram": ["nova-3"],
    }

    def __init__(self):
        super().__init__()
        self._deepgram_api_key = None

        self.setWindowTitle("As-Recorded Reviewer")
        self.resize(600, 360)
        self.setFixedHeight(360)

        container = QWidget()
        self.setCentralWidget(container)
        layout_main = QVBoxLayout(container)

        # TITLE
        label_title = QLabel("<font size=6>Speech to text tool</font>")
        label_title.setAlignment(Qt.AlignHCenter)
        layout_main.addWidget(label_title)

        # GRID
        grid = QGridLayout()

        # MODE
        grid.addWidget(QLabel("Modo:"), 0, 0)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Compare", "Transcribe-Only"])
        # Conectar cambio de modo para habilitar/deshabilitar campos dependientes
        self.combo_mode.currentIndexChanged.connect(self.update_input_states)
        grid.addWidget(self.combo_mode, 0, 1)

        # ENGINE
        grid.addWidget(QLabel("Motor:"), 1, 0)
        self.combo_engine = QComboBox()
        self.combo_engine.addItem("Whisper", "whisper")
        self.combo_engine.addItem("Deepgram", "deepgram")
        self.combo_engine.currentIndexChanged.connect(self.update_model_options)
        self.combo_engine.currentIndexChanged.connect(self.update_input_states)
        grid.addWidget(self.combo_engine, 1, 1)

        # MODEL
        grid.addWidget(QLabel("Modelo:"), 2, 0)
        self.combo_model = QComboBox()
        grid.addWidget(self.combo_model, 2, 1)
        self.update_model_options()

        # LANGUAGE (ComboBox con datos internos)
        grid.addWidget(QLabel("Idioma:"), 3, 0)
        self.combo_lang = QComboBox()
        # Usamos itemData para guardar el código ISO ("es") mientras mostramos el nombre
        languages = [
            ("Español (ES/MX)", "es"),
            ("English (EN)", "en"),
            ("Português (BR/PT)", "pt"),
            ("Français (FR)", "fr"),
            ("Deutsch (DE)", "de"),
            ("Italiano (IT)", "it"),
            ("日本語 (JA)", "ja")
        ]
        for name, code in languages:
            self.combo_lang.addItem(name, code)
        
        grid.addWidget(self.combo_lang, 3, 1)

        # AUDIO FOLDER
        grid.addWidget(QLabel("Carpeta audios:"), 4, 0)
        self.input_audio = QLineEdit()
        self.input_audio.textChanged.connect(self.sync_output_with_audio_folder)
        btn_audio = QPushButton("Browse")
        btn_audio.clicked.connect(self.select_audio_folder)
        grid.addWidget(self.input_audio, 4, 1)
        grid.addWidget(btn_audio, 4, 2)

        # EXCEL (Widgets con self para poder desactivarlos)
        self.label_excel = QLabel("Script:")
        grid.addWidget(self.label_excel, 5, 0)
        self.input_excel = QLineEdit()
        self.btn_excel = QPushButton("Browse")
        self.btn_excel.clicked.connect(self.select_excel)
        grid.addWidget(self.input_excel, 5, 1)
        grid.addWidget(self.btn_excel, 5, 2)

        # GLOSSARY (solo aplica para Deepgram en modo Compare)
        self.label_glossary = QLabel("Glosario:")
        grid.addWidget(self.label_glossary, 6, 0)
        self.input_glossary = QLineEdit()
        self.btn_glossary = QPushButton("Browse")
        self.btn_glossary.clicked.connect(self.select_glossary)
        grid.addWidget(self.input_glossary, 6, 1)
        grid.addWidget(self.btn_glossary, 6, 2)

        # OUTPUT
        grid.addWidget(QLabel("Output:"), 7, 0)
        self.input_output = QLineEdit("resultado.xlsx")
        btn_output = QPushButton("Browse")
        btn_output.clicked.connect(self.select_output)
        grid.addWidget(self.input_output, 7, 1)
        grid.addWidget(btn_output, 7, 2)

        layout_main.addLayout(grid)

        # RUN BUTTON
        btn_run = QPushButton("Run")
        btn_run.setStyleSheet("font-weight: bold; height: 30px; max-width: 160px;")
        btn_run.clicked.connect(self.run_process)
        btn_run.setFixedWidth(160)
        layout_main.addWidget(btn_run)
        layout_main.setAlignment(btn_run, Qt.AlignHCenter)

        center_app(self, 600, 360)
        self.setFixedSize(600, 360) # Si quieres que no se pueda estirar
        self.update_input_states()

    # -------- MÉTODOS DE INTERFAZ --------

    def update_input_states(self):
        """Actualiza disponibilidad de Script y Glosario según modo/motor."""
        is_compare = self.combo_mode.currentText() == "Compare"
        is_deepgram = self.combo_engine.currentData() == "deepgram"

        self.label_excel.setEnabled(is_compare)
        self.input_excel.setEnabled(is_compare)
        self.btn_excel.setEnabled(is_compare)

        glossary_enabled = is_deepgram
        self.label_glossary.setEnabled(glossary_enabled)
        self.input_glossary.setEnabled(glossary_enabled)
        self.btn_glossary.setEnabled(glossary_enabled)

        if not is_compare:
            self.input_excel.clear()
        if not glossary_enabled:
            self.input_glossary.clear()

    def update_model_options(self):
        """Actualiza los modelos disponibles según el motor seleccionado."""
        engine = self.combo_engine.currentData()
        models = self.ENGINE_MODELS.get(engine, [])
        self.combo_model.clear()
        self.combo_model.addItems(models)
        if engine == "whisper" and "Medium" in models:
            self.combo_model.setCurrentText("Medium")

    # -------- MÉTODOS DE SELECCIÓN --------

    def select_audio_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select audio folder")
        if folder:
            self.input_audio.setText(folder)

    def sync_output_with_audio_folder(self, _text=None):
        audio_folder = self.input_audio.text().strip()
        if not audio_folder:
            return
        self.input_output.setText(os.path.join(audio_folder, "resultado.xlsx"))

    def select_excel(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Excel", filter="Excel (*.xlsx)")
        if file:
            self.input_excel.setText(file)

    def select_glossary(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Glossary", filter="Excel (*.xlsx)")
        if file:
            self.input_glossary.setText(file)

    def select_output(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save Output", filter="Excel (*.xlsx)")
        if file:
            self.input_output.setText(file)

    # -------- PROCESO PRINCIPAL --------

    def run_process(self):
        try:
            mode = self.combo_mode.currentText()
            audio_folder = self.input_audio.text()
            excel = self.input_excel.text()
            glossary_path = self.input_glossary.text()
            output = self.input_output.text()
            model = self.combo_model.currentText().lower()
            engine = self.combo_engine.currentData()
            
            # Obtenemos el código ISO (ej: "es") almacenado en el itemData
            language = self.combo_lang.currentData()

            if not audio_folder:
                QMessageBox.warning(self, "Error", "Selecciona carpeta de audios")
                return

            if mode == "Compare" and not excel:
                QMessageBox.warning(self, "Error", "Selecciona Excel para comparar")
                return

            # Ejecución del Core
            if engine == "whisper":
                transcriber = core.WhisperTranscriber(model_size=model)
            elif engine == "deepgram":
                if not self._deepgram_api_key:
                    deepgram_api_key, ok = QInputDialog.getText(
                        self,
                        "Deepgram API Key",
                        "Pega tu DEEPGRAM_API_KEY:",
                        QLineEdit.Password,
                    )
                    deepgram_api_key = deepgram_api_key.strip()
                    if not ok or not deepgram_api_key:
                        QMessageBox.warning(self, "Error", "Debes ingresar una DEEPGRAM_API_KEY válida")
                        return
                    self._deepgram_api_key = deepgram_api_key
                deepgram_workers = int(os.getenv("DEEPGRAM_MAX_WORKERS", "4"))
                transcriber = core.DeepgramTranscriber(
                    api_key=self._deepgram_api_key,
                    model=model,
                    max_workers=deepgram_workers,
                    glossary_path=glossary_path or None,
                )
            else:
                raise ValueError(f"Motor no soportado: {engine}")

            transcripts = core.transcribe_folder(
                transcriber=transcriber,
                folder_path=audio_folder,
                language=language,
            )

            if mode == "Transcribe-Only":
                core.export_transcriptions_to_excel(transcripts, output)
            else:
                core.compare_with_excel(
                    excel_path=excel,
                    transcripts=transcripts,
                    audio_column="Filename",
                    expected_column="Script",
                    output_path=output,
                    sheet_name=None,
                )

            QMessageBox.information(self, "OK", "Proceso completado exitosamente")

        except Exception as e:
            error_text = str(e)
            if self.combo_engine.currentData() == "deepgram" and ("401" in error_text or "unauthorized" in error_text.lower()):
                self._deepgram_api_key = None
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
