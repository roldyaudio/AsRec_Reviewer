import os
from pathlib import Path

from lib_installer import (
    ensure_pip,
    install_pytorch_cuda_forced,
    install_requirements_in_directory,
)

APP_DIR = Path(__file__).resolve().parent
LOCAL_STT_DEPENDENCIES = {"openai-whisper", "pydub", "torch", "torchvision", "torchaudio"}

ensure_pip()
install_requirements_in_directory(APP_DIR, skip_packages=LOCAL_STT_DEPENDENCIES)

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt

# Import your existing logic
import transcribe_or_compare as core


def center_app(app_window, app_width: int, app_height: int):
    """Centers the window to the main display/monitor using PySide6."""
    app_window.resize(app_width, app_height)
    screen = QGuiApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()

    x = int((screen_geometry.width() / 2.5) - app_width)
    y = int((screen_geometry.height() / 2) - (app_height / 2))

    app_window.move(screen_geometry.x() + x, screen_geometry.y() + y)


class MainWindow(QMainWindow):
    ENGINE_MODELS = {
        "whisper": ["Tiny", "Base", "Small", "Medium", "Large", "Large-v3"],
        "deepgram": ["nova-3"],
    }

    def __init__(self):
        super().__init__()
        self._deepgram_api_key = None

        self.setWindowTitle("As-Recorded Reviewer")

        container = QWidget()
        self.setCentralWidget(container)
        layout_main = QVBoxLayout(container)

        label_title = QLabel("<font size=6>Asrec Reviewer</font>")
        label_title.setAlignment(Qt.AlignHCenter)
        layout_main.addWidget(label_title)

        layout_main.addWidget(self._build_engine_language_section(), alignment=Qt.AlignmentFlag.AlignCenter)
        layout_main.addWidget(self._build_paths_section())
        layout_main.addWidget(self._build_qa_section(), alignment=Qt.AlignmentFlag.AlignCenter)
        

        btn_run = QPushButton("Run")
        btn_run.setStyleSheet("font-weight: bold; height: 30px; max-width: 160px;")
        btn_run.clicked.connect(self.run_process)
        btn_run.setFixedWidth(160)
        layout_main.addWidget(btn_run)
        layout_main.setAlignment(btn_run, Qt.AlignHCenter)

        center_app(self, 660, 460)
        #self.setFixedSize(660, 460)
        self.update_input_states()

    def _build_engine_language_section(self) -> QGroupBox:
        group = QGroupBox("  Engine and Language  ")
        group.setFixedWidth(520)

        grid = QGridLayout(group)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        def add_field(label_text: str, widget: QWidget, row: int, column: int):
            field = QWidget()
            field_layout = QGridLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setHorizontalSpacing(6)

            label = QLabel(label_text)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            field_layout.addWidget(label, 0, 0)
            field_layout.addWidget(widget, 0, 1)
            field_layout.setColumnStretch(1, 1)

            grid.addWidget(field, row, column)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Compare", "Transcribe-Only"])
        self.combo_mode.currentIndexChanged.connect(self.update_input_states)
        add_field("Mode:  ", self.combo_mode, 0, 0)

        self.combo_lang = QComboBox()
        languages = [
            ("Español (ES/MX)", "es"),
            ("English (EN)", "en"),
            ("Português (BR/PT)", "pt"),
            ("Français (FR)", "fr"),
            ("Deutsch (DE)", "de"),
            ("Italiano (IT)", "it"),
            ("日本語 (JA)", "ja"),
            ("中文 (ZH/CN)", "zh"),
            ("한국어 (KO)", "ko"),
            ("ไทย (TH)", "th"),
        ]
        for name, code in languages:
            self.combo_lang.addItem(name, code)
        add_field("Language:", self.combo_lang, 0, 1)

        self.combo_engine = QComboBox()
        self.combo_engine.addItem("Deepgram", "deepgram")
        self.combo_engine.addItem("Whisper", "whisper")
        self.combo_engine.currentIndexChanged.connect(self.update_model_options)
        self.combo_engine.currentIndexChanged.connect(self.update_input_states)
        add_field("Engine:", self.combo_engine, 1, 0)

        self.combo_model = QComboBox()
        add_field("Model:      ", self.combo_model, 1, 1)
        self.update_model_options()

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        return group

    def _build_paths_section(self) -> QGroupBox:
        group = QGroupBox("  Paths  ")
        grid = QGridLayout(group)

        grid.addWidget(QLabel("Audio file folder:"), 0, 0)
        self.input_audio = QLineEdit()
        self.input_audio.textChanged.connect(self.sync_output_with_audio_folder)
        btn_audio = QPushButton("Browse")
        btn_audio.clicked.connect(self.select_audio_folder)
        grid.addWidget(self.input_audio, 0, 1)
        grid.addWidget(btn_audio, 0, 2)

        self.label_excel = QLabel("Script:")
        grid.addWidget(self.label_excel, 1, 0)
        self.input_excel = QLineEdit()
        self.btn_excel = QPushButton("Browse")
        self.btn_excel.clicked.connect(self.select_excel)
        grid.addWidget(self.input_excel, 1, 1)
        grid.addWidget(self.btn_excel, 1, 2)

        self.label_glossary = QLabel("Glossary:")
        grid.addWidget(self.label_glossary, 2, 0)
        self.input_glossary = QLineEdit()
        self.btn_glossary = QPushButton("Browse")
        self.btn_glossary.clicked.connect(self.select_glossary)
        grid.addWidget(self.input_glossary, 2, 1)
        grid.addWidget(self.btn_glossary, 2, 2)

        grid.addWidget(QLabel("Output file:"), 3, 0)
        self.input_output = QLineEdit("resultado.xlsx")
        btn_output = QPushButton("Browse")
        btn_output.clicked.connect(self.select_output)
        grid.addWidget(self.input_output, 3, 1)
        grid.addWidget(btn_output, 3, 2)

        return group

    def _build_qa_section(self) -> QGroupBox:
        group = QGroupBox("  Quality Warnings  ")
        group.setFixedWidth(300)
        grid = QGridLayout(group)

        self.check_generate_qa = QCheckBox("Generate Warning session.")
        self.check_generate_qa.setToolTip(
            "Creates a .rpp file next to the Excel output with one track per quality value."
        )
        grid.addWidget(self.check_generate_qa, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        self.check_dry_run = QCheckBox("Validate only (dry run).")
        self.check_dry_run.setToolTip(
            "Validates audio/Excel matches and writes a log without transcribing or calling Deepgram."
        )
        grid.addWidget(self.check_dry_run, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        return group

    # -------- MÉTODOS DE INTERFAZ --------

    def update_input_states(self):
        """Actualiza disponibilidad de Script, Glosario y QA según modo/motor."""
        is_compare = self.combo_mode.currentText() == "Compare"
        is_deepgram = self.combo_engine.currentData() == "deepgram"

        self.label_excel.setEnabled(is_compare)
        self.input_excel.setEnabled(is_compare)
        self.btn_excel.setEnabled(is_compare)

        self.check_generate_qa.setEnabled(is_compare)
        if not is_compare:
            self.check_generate_qa.setChecked(False)

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
        file, _ = QFileDialog.getOpenFileName(self, "Select Script", filter="Excel (*.xlsx)")
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
            audio_folder = self.input_audio.text().strip()
            excel = self.input_excel.text().strip()
            glossary_path = self.input_glossary.text().strip()
            output = self.input_output.text().strip()
            model = self.combo_model.currentText().lower()
            engine = self.combo_engine.currentData()
            generate_qa = self.check_generate_qa.isChecked()
            dry_run = self.check_dry_run.isChecked()

            language = self.combo_lang.currentData()

            if not audio_folder:
                QMessageBox.warning(self, "Error", "Select an audio file folder")
                return

            if mode == "Compare" and not excel:
                QMessageBox.warning(self, "Error", "Select a Script file to compare")
                return

            if not output:
                QMessageBox.warning(self, "Error", "Select an output file")
                return

            output_path = Path(output)
            if output_path.exists() and output_path.is_dir():
                output_path = output_path / "resultado.xlsx"
            elif output_path.suffix.lower() != ".xlsx":
                output_path = output_path.with_suffix(".xlsx")

            with core.run_logging(output_path=str(output_path)) as log_path:
                core.validate_inputs(
                    audio_folder=audio_folder,
                    excel_path=excel if mode == "Compare" else None,
                    audio_column="Filename",
                    sheet_name=None,
                )

                if dry_run:
                    QMessageBox.information(
                        self,
                        "Dry run completed",
                        f"Validation completed without transcribing.\nLog: {log_path}",
                    )
                    return

                if engine == "whisper":
                    install_pytorch_cuda_forced()
                    install_requirements_in_directory(
                        APP_DIR,
                        only_packages=LOCAL_STT_DEPENDENCIES,
                    )
                    transcriber = core.WhisperTranscriber(model_size=model)
                elif engine == "deepgram":
                    if not self._deepgram_api_key:
                        deepgram_api_key, ok = QInputDialog.getText(
                            self,
                            "Deepgram API Key",
                            "Paste your DEEPGRAM_API_KEY:",
                            QLineEdit.Password,
                        )
                        deepgram_api_key = deepgram_api_key.strip()
                        if not ok or not deepgram_api_key:
                            QMessageBox.warning(self, "Error", "You must enter a valid DEEPGRAM_API_KEY")
                            return
                        self._deepgram_api_key = deepgram_api_key
                    deepgram_workers = int(os.getenv("DEEPGRAM_MAX_WORKERS", "4"))
                    deepgram_retries = int(os.getenv("DEEPGRAM_MAX_RETRIES", str(core.DEFAULT_DEEPGRAM_RETRIES)))
                    deepgram_backoff = float(
                        os.getenv(
                            "DEEPGRAM_RETRY_BACKOFF_SECONDS",
                            str(core.DEFAULT_DEEPGRAM_RETRY_BACKOFF_SECONDS),
                        )
                    )
                    transcriber = core.DeepgramTranscriber(
                        api_key=self._deepgram_api_key,
                        model=model,
                        max_workers=deepgram_workers,
                        glossary_path=glossary_path or None,
                        max_retries=deepgram_retries,
                        retry_backoff_seconds=deepgram_backoff,
                    )
                else:
                    raise ValueError(f"Unsupported engine: {engine}")

                transcripts = core.transcribe_folder(
                    transcriber=transcriber,
                    folder_path=audio_folder,
                    language=language,
                )
                core.summarize_transcriptions(transcripts)

                qa_output = None
                if mode == "Transcribe-Only":
                    core.export_transcriptions_to_excel(transcripts, str(output_path))
                else:
                    results = core.compare_with_excel(
                        excel_path=excel,
                        transcripts=transcripts,
                        audio_column="Filename",
                        expected_column="Script",
                        output_path=str(output_path),
                        sheet_name=None,
                        language=language,
                    )
                    if generate_qa:
                        qa_output = core.export_qa_reaper_project(
                            audio_folder=audio_folder,
                            results=results,
                            output_path=output_path.with_name(f"{output_path.stem}_qa.rpp"),
                        )

                message = "Process completed successfully"
                if qa_output:
                    message += f"\nQA Reaper project: {qa_output}"
                message += f"\nLog: {log_path}"
                QMessageBox.information(self, "OK", message)

        except Exception as e:
            error_text = str(e)
            if self.combo_engine.currentData() == "deepgram" and (
                "401" in error_text or "unauthorized" in error_text.lower()
            ):
                self._deepgram_api_key = None
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
