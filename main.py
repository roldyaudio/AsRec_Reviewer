from lib_installer import *

install_requirements_in_directory("C:/Apps/AsRec_Reviewer")

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMessageBox, QPushButton, QWidget,
    QVBoxLayout, QGridLayout, QLineEdit, QFileDialog, QComboBox
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
    x = int((screen_geometry.width() / 2) - (app_width / 2))
    y = int((screen_geometry.height() / 5) - (app_height / 2))
    
    app_window.move(screen_geometry.x() + x, screen_geometry.y() + y)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("As-Recorded Reviewer")
        self.resize(600, 250)
        self.setFixedHeight(250)

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
        # Conectar cambio de modo para habilitar/deshabilitar Excel
        self.combo_mode.currentIndexChanged.connect(self.toggle_excel_fields)
        grid.addWidget(self.combo_mode, 0, 1)

        # AUDIO FOLDER
        grid.addWidget(QLabel("Carpeta audios:"), 1, 0)
        self.input_audio = QLineEdit()
        btn_audio = QPushButton("Browse")
        btn_audio.clicked.connect(self.select_audio_folder)
        grid.addWidget(self.input_audio, 1, 1)
        grid.addWidget(btn_audio, 1, 2)

        # EXCEL (Widgets con self para poder desactivarlos)
        self.label_excel = QLabel("Script:")
        grid.addWidget(self.label_excel, 2, 0)
        self.input_excel = QLineEdit()
        self.btn_excel = QPushButton("Browse")
        self.btn_excel.clicked.connect(self.select_excel)
        grid.addWidget(self.input_excel, 2, 1)
        grid.addWidget(self.btn_excel, 2, 2)

        # OUTPUT
        grid.addWidget(QLabel("Output:"), 3, 0)
        self.input_output = QLineEdit("resultado.xlsx")
        btn_output = QPushButton("Browse")
        btn_output.clicked.connect(self.select_output)
        grid.addWidget(self.input_output, 3, 1)
        grid.addWidget(btn_output, 3, 2)

        # MODEL
        grid.addWidget(QLabel("Modelo:"), 4, 0)
        self.combo_model = QComboBox()
        # Añadimos "Large-v3" a la lista
        self.combo_model.addItems(["Tiny", "Base", "Small", "Medium", "Large", "Large-v3"]) 
        self.combo_model.setCurrentText("Medium")
        grid.addWidget(self.combo_model, 4, 1)

        # LANGUAGE (ComboBox con datos internos)
        grid.addWidget(QLabel("Idioma:"), 5, 0)
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
        
        grid.addWidget(self.combo_lang, 5, 1)

        layout_main.addLayout(grid)

        # RUN BUTTON
        btn_run = QPushButton("Run")
        btn_run.setStyleSheet("font-weight: bold; height: 30px;")
        btn_run.clicked.connect(self.run_process)
        layout_main.addWidget(btn_run)

        center_app(self, 600, 250)
        self.setFixedSize(600, 250) # Si quieres que no se pueda estirar

    # -------- MÉTODOS DE INTERFAZ --------

    def toggle_excel_fields(self):
        """Desactiva visualmente los campos de Excel si el modo es Transcribe-Only."""
        is_compare = self.combo_mode.currentText() == "Compare"
        self.label_excel.setEnabled(is_compare)
        self.input_excel.setEnabled(is_compare)
        self.btn_excel.setEnabled(is_compare)
        
        if not is_compare:
            self.input_excel.clear()

    # -------- MÉTODOS DE SELECCIÓN --------

    def select_audio_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select audio folder")
        if folder:
            self.input_audio.setText(folder)

    def select_excel(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Excel", filter="Excel (*.xlsx)")
        if file:
            self.input_excel.setText(file)

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
            output = self.input_output.text()
            model = self.combo_model.currentText().lower()
            
            # Obtenemos el código ISO (ej: "es") almacenado en el itemData
            language = self.combo_lang.currentData()

            if not audio_folder:
                QMessageBox.warning(self, "Error", "Selecciona carpeta de audios")
                return

            if mode == "Compare" and not excel:
                QMessageBox.warning(self, "Error", "Selecciona Excel para comparar")
                return

            # Ejecución del Core
            transcriber = core.WhisperTranscriber(model_size=model)

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
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
