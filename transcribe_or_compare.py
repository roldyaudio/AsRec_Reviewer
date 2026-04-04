import argparse
import os
import sys
import re
import unicodedata
from rapidfuzz import fuzz
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from pydub import AudioSegment
from pydub.silence import split_on_silence
from collections import Counter
import tempfile
import pandas as pd
import torch
from openpyxl import load_workbook
from openpyxl.styles import PatternFill


# Colores para Excel
GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")


class BaseTranscriber:
    """Interfaz base para cambiar f谩cilmente el backend de transcripci贸n."""

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        raise NotImplementedError


class WhisperTranscriber(BaseTranscriber):
    """Implementaci贸n con OpenAI Whisper local."""

    def __init__(self, model_size: str = "medium"):
        import whisper

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_size = model_size
        
        print(f"[INFO] Usando dispositivo: {self.device}")
        print(f"[INFO] Cargando modelo Whisper: {model_size}")
        
        # Whisper cargará automáticamente large-v3 si pasas ese string
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        kwargs = {"fp16": self.device == "cuda"}
        if language:
            kwargs["language"] = language

        # 1. Obtener duración para decidir si segmentar
        audio = AudioSegment.from_file(audio_path)
        duration_secs = len(audio) / 1000.0

        # 2. Si el audio es corto (ej. menos de 15s), transcribir directo
        if duration_secs < 15.0:
            result = self.model.transcribe(audio_path, **kwargs)
            return result.get("text", "").strip()

        # 3. Solo si es un audio largo, usar la lógica de chunks (opcional)
        chunks = split_on_silence(
            audio,
            min_silence_len=700, # Aumentado para evitar micro-segmentos
            silence_thresh=-45,
            keep_silence=500     # Más margen ayuda a Whisper a entender el inicio/fin
        )
        
        print(f"[DEBUG] N煤mero de chunks: {len(chunks)}")
        
        if not chunks:
            print("[WARN] Silence split fall贸, usando transcripci贸n directa.")
            result = self.model.transcribe(audio_path, **kwargs)
            return result.get("text", "").strip()

        full_text = []
        print(f"[INFO] Procesando {len(chunks)} chunks...")

        for i, chunk in enumerate(chunks):
            # 1. Validaci贸n previa: Si el chunk es muy corto, ni siquiera creamos el temporal
            if len(chunk) < 500:
                continue

            # 2. Crear el archivo temporal pero con delete=False para manejarlo nosotros
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                # Exportar el audio al archivo temporal
                chunk.export(tmp.name, format="wav")
                
                # 3. 隆IMPORTANTE! Cerramos el puntero del archivo para que Windows/Linux 
                # permitan que Whisper lo abra sin bloqueos.
                tmp.close()

                # Transcribir usando la ruta del archivo
                result = self.model.transcribe(tmp.name, **kwargs)
                text = result.get("text", "").strip()

                if text:
                    full_text.append(text)

            except Exception as e:
                print(f"[ERROR] Chunk {i} fall贸: {e}")

            finally:
                # 4. Limpieza garantizada: Si el archivo existe, se borra s铆 o s铆.
                if os.path.exists(tmp.name):
                    try:
                        os.remove(tmp.name)
                    except Exception as e:
                        print(f"[WARN] No se pudo borrar temporal {tmp.name}: {e}")
        print(f"Proceso completado")
        return " ".join(full_text).strip()


@dataclass
class ComparisonResult:
    audio_file: str
    transcript: str
    expected_text: str
    match: Optional[bool]  # True/False/None(no evaluable)


@dataclass
class TranscriptionOnlyResult:
    audio_file: str
    transcript: str


def get_audio_files(folder_path: str, extensions: Iterable[str] = (".wav", ".mp3", ".m4a")) -> List[str]:
    audio_files: List[str] = []
    allowed = tuple(ext.lower() for ext in extensions)

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(allowed):
                audio_files.append(os.path.join(root, file))

    audio_files.sort()
    return audio_files


def normalize_text(text: str) -> str:
    """
    Normaliza para comparaci贸n robusta:
    - min煤sculas
    - elimina tildes
    - quita puntuaci贸n
    - compacta espacios
    """
    text = text or ""
    text = text.lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fuzzy_match(expected: str, transcript: str, threshold: int = 95) -> Optional[bool]:
    exp_norm = normalize_text(expected)
    tr_norm = normalize_text(transcript)

    if not exp_norm or not tr_norm:
        return None

    ratio = fuzz.token_sort_ratio(exp_norm, tr_norm)

    if ratio >= threshold:
        if has_word_difference(exp_norm, tr_norm):
            return None  # 🟡 palabras distintas aunque sea similar
        return True     # 🟢 match real

    return False        # 🔴 no cumple threshold

def has_word_difference(a: str, b: str) -> bool:
    return Counter(a.split()) != Counter(b.split())

def transcribe_folder(
    transcriber: BaseTranscriber,
    folder_path: str,
    language: Optional[str] = "es",
) -> Dict[str, str]:
    files = get_audio_files(folder_path)
    if not files:
        print("[WARN] No se encontraron archivos de audio.")
        return {}

    transcripts: Dict[str, str] = {}
    for idx, audio_path in enumerate(files, start=1):
        relative_path = os.path.relpath(audio_path, folder_path)
        print(f"[{idx}/{len(files)}] Transcribiendo: {relative_path}")
        try:
            transcripts[relative_path] = transcriber.transcribe(audio_path, language=language)
        except Exception as exc:
            print(f"[ERROR] Fall贸 {relative_path}: {exc}")
            transcripts[relative_path] = ""

    return transcripts


def highlight_differences(expected: str, transcript: str) -> str:
    """
    Genera una versi贸n del texto donde las diferencias se marcan con ~rojo~ (simbolizado con caracteres especiales).
    Excel no soporta estilos parciales f谩cilmente, as铆 que usamos celdas completas coloreadas,
    pero podemos marcar diferencias con alg煤n prefijo/sufijo si queremos m谩s detalle.
    """
    exp_words = expected.split()
    tr_words = transcript.split()
    highlighted = []

    for w in tr_words:
        # buscamos si la palabra existe en expected con tolerancia
        match_found = any(fuzz.ratio(w, ew) > 85 for ew in exp_words)

        if match_found:
            highlighted.append(w)
        else:
            highlighted.append(f"*{w.upper()}*")
    return " ".join(highlighted)
    

def export_transcriptions_to_excel(
    transcripts: Dict[str, str],
    output_path: str,
) -> List[TranscriptionOnlyResult]:
    # Si el usuario pasa una carpeta en lugar de archivo, agregamos un nombre por defecto
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "resultado.xlsx")

    # Aseguramos que tenga la extensi贸n .xlsx
    if not output_path.lower().endswith(".xlsx"):
        output_path += ".xlsx"

    # Creamos la lista de resultados
    rows: List[TranscriptionOnlyResult] = [
        TranscriptionOnlyResult(audio_file=audio_file, transcript=transcript)
        for audio_file, transcript in sorted(transcripts.items())
    ]

    # Creamos el DataFrame
    df = pd.DataFrame([
        {"audio_file": row.audio_file, "transcripcion": row.transcript} 
        for row in rows
    ])

    # Guardamos en Excel
    df.to_excel(output_path, index=False)

    return rows


def compare_with_excel(
    excel_path: str,
    transcripts: Dict[str, str],
    audio_column: str,
    expected_column: str,
    output_path: str,
    sheet_name: Optional[str] = None,
) -> List[ComparisonResult]:
    # Si el usuario pasa una carpeta en lugar de archivo, agregamos un nombre por defecto
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "resultado_comparacion.xlsx")

    # Aseguramos que tenga la extensi贸n .xlsx
    if not output_path.lower().endswith(".xlsx"):
        output_path += ".xlsx"

    # Leemos Excel de entrada
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    if isinstance(df, dict):
        print("[WARN] Se detectaron m煤ltiples hojas, usando la primera.")
        df = list(df.values())[0]

    if audio_column not in df.columns or expected_column not in df.columns:
        raise ValueError(
            f"Columnas inv谩lidas. Encontradas: {list(df.columns)} | "
            f"Esperadas: '{audio_column}' y '{expected_column}'"
        )

    results: List[ComparisonResult] = []
    transcript_list: List[str] = []
    match_list: List[Optional[bool]] = []

    for _, row in df.iterrows():
        audio_name = str(row[audio_column]).strip()
        expected_text = str(row[expected_column]) if pd.notna(row[expected_column]) else ""

        transcript = transcripts.get(audio_name, "")
        match = fuzzy_match(expected_text, transcript)

        results.append(
            ComparisonResult(
                audio_file=audio_name,
                transcript=transcript,
                expected_text=expected_text,
                match=match,
            )
        )
        transcript_list.append(transcript)
        match_list.append(match)

    df["transcripcion"] = transcript_list
    df["coincide"] = match_list
    df.to_excel(output_path, index=False)

    # Pintar en colores usando openpyxl
    wb = load_workbook(output_path)
    ws = wb[sheet_name] if sheet_name else wb.active

    expected_col_idx = list(df.columns).index(expected_column) + 1
    transcript_col_idx = list(df.columns).index("transcripcion") + 1
    match_col_idx = list(df.columns).index("coincide") + 1

    for row_idx, value in enumerate(match_list, start=2):
        expected_cell = ws.cell(row=row_idx, column=expected_col_idx)
        transcript_cell = ws.cell(row=row_idx, column=transcript_col_idx)
        match_cell = ws.cell(row=row_idx, column=match_col_idx)

        if value is True:
            match_cell.fill = GREEN_FILL

        elif value is False:
            # Solo modificas el texto si quieres marcar diferencias
            transcript_cell.value = highlight_differences(expected_cell.value, transcript_cell.value)
            match_cell.fill = RED_FILL

        else:
            match_cell.fill = YELLOW_FILL
    wb.save(output_path)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audios y opcionalmente compara contra un Excel de guion."
    )
    parser.add_argument(
        "--mode",
        choices=["compare", "transcribe-only"],
        default="compare",
        help="compare: compara contra Excel. transcribe-only: solo transcribe y exporta a nuevo Excel.",
    )
    parser.add_argument("--audio-folder", required=False, help="Carpeta con audios")
    parser.add_argument("--excel", required=False, help="Ruta del Excel de entrada (solo modo compare)")
    parser.add_argument(
        "--audio-column",
        default="audio_file",
        help="Nombre de columna con nombre/ruta relativa del audio",
    )
    parser.add_argument(
        "--expected-column",
        default="guion",
        help="Nombre de columna con texto esperado",
    )
    parser.add_argument("--sheet", default=None, help="Nombre de hoja en Excel (opcional)")
    parser.add_argument(
        "--output",
        default="resultado_comparacion.xlsx",
        help="Ruta del Excel de salida",
    )
    # Busca esta sección en parse_args()
    parser.add_argument(
        "--model-size",
        default="medium",
        help="Modelo Whisper (tiny/base/small/medium/large/large-v3)", # Añadido large-v3
    )
    parser.add_argument(
        "--language",
        default="es",
        help="Idioma forzado (ej. es, en) o vac铆o para autodetectar",
    )

    return parser.parse_args()


def ask_input(prompt: str, default: Optional[str] = None) -> str:
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        if value == "":
            value = default
    else:
        value = input(f"{prompt}: ").strip()
    return value.strip().strip('"').strip("'")


def main() -> None:
    args = parse_args()

    # 馃憞 DETECTAR DOBLE CLICK / SIN ARGUMENTOS
    interactive_mode = len(sys.argv) == 1

    if interactive_mode:
        print("\n=== MODO INTERACTIVO ===\n")

        args.mode = ask_input(
            "Modo (1=compare, 2=transcribe-only)",
            "1"
        )

        args.mode = "compare" if args.mode == "1" else "transcribe-only"

        args.audio_folder = ask_input("Ruta de carpeta de audios")

        if args.mode == "compare":
            args.excel = ask_input("Ruta del Excel")

            args.audio_column = ask_input(
                "Columna de audio",
                args.audio_column
            )

            args.expected_column = ask_input(
                "Columna de texto esperado",
                args.expected_column
            )

            args.sheet = ask_input(
                "Nombre de hoja (Enter = primera)",
                ""
            ) or None

            args.output = ask_input(
                "Ruta de salida",
                "resultado_comparacion.xlsx"
            )

        else:  # transcribe-only
            args.output = ask_input(
                "Ruta de salida",
                "solo_transcripciones.xlsx"
            )

        args.model_size = ask_input(
            "Modelo Whisper",
            args.model_size
        )

        args.language = ask_input(
            "Idioma (es/en/... o vac铆o auto)",
            args.language
        )

    # 馃憞 VALIDACI脫N m铆nima (por si viene por CLI)
    if not args.audio_folder:
        args.audio_folder = ask_input("Ruta de carpeta de audios")

    if args.mode == "compare" and not args.excel:
        args.excel = ask_input("Ruta del Excel")

    if not args.output:
        args.output = ask_input("Ruta de salida", "resultado.xlsx")

    print("\n[INFO] Configuraci贸n final:")
    print(f"Modo: {args.mode}")
    print(f"Audios: {args.audio_folder}")
    print(f"Output: {args.output}")
    print()

    # 馃敟 EJECUCI脫N
    transcriber = WhisperTranscriber(model_size=args.model_size)
    language = args.language if args.language else None

    transcripts = transcribe_folder(
        transcriber=transcriber,
        folder_path=args.audio_folder,
        language=language,
    )

    if args.mode == "transcribe-only":
        rows = export_transcriptions_to_excel(
            transcripts=transcripts,
            output_path=args.output
        )

        print("\n=== Resumen (solo transcripci贸n) ===")
        print(f"Audios procesados: {len(rows)}")
        print(f"Salida: {args.output}")

        if interactive_mode:
            input("\nPresiona Enter para cerrar...")

        return

    # 馃憞 modo compare
    results = compare_with_excel(
        excel_path=args.excel,
        transcripts=transcripts,
        audio_column=args.audio_column,
        expected_column=args.expected_column,
        output_path=args.output,
        sheet_name=args.sheet,
    )

    total = len(results)
    ok = sum(1 for x in results if x.match is True)
    bad = sum(1 for x in results if x.match is False)
    unk = sum(1 for x in results if x.match is None)

    print("\n=== Resumen ===")
    print(f"Total filas: {total}")
    print(f"Coinciden (verde): {ok}")
    print(f"No coinciden (rojo): {bad}")
    print(f"Sin evaluar (amarillo): {unk}")
    print(f"Salida: {args.output}")

    if interactive_mode:
        input("\nPresiona Enter para cerrar...")


if __name__ == "__main__":
    main()
