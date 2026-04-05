# AsRec Reviewer

Herramienta de **Speech-to-Text (STT)** con interfaz gráfica (PySide6) para:

1. **Compare**: transcribir audios y compararlos contra un Excel de referencia.
2. **Transcribe-Only**: transcribir audios y exportar resultados a un Excel nuevo.

## Novedades principales

- ✅ **Motor seleccionable**:
  - **Whisper local** (CPU/GPU).
  - **Deepgram API** (modelo `nova-3`).
- ✅ **Paralelismo con workers** para Deepgram usando `ThreadPoolExecutor`.
- ✅ **Ingreso de API Key de Deepgram** desde la UI (prompt seguro tipo password).
- ✅ Soporte de modelo Whisper `large-v3`.
- ✅ Detección recursiva de audio (`.wav`, `.mp3`, `.m4a`).
- ✅ Resaltado visual de resultados en Excel (`coincide`: verde/rojo/amarillo).

---

## Requisitos

- Python 3.10+
- FFmpeg en `PATH` (requerido por `pydub`)

Instalación rápida:

```bash
pip install -r requirements.txt
```

Dependencias principales:
- `PySide6`
- `openai-whisper`
- `torch`
- `deepgram-sdk`
- `pandas`
- `openpyxl`
- `rapidfuzz`
- `pydub`

> Nota: Whisper usa CUDA automáticamente si `torch.cuda.is_available()` es verdadero.

---

## Ejecución

```bash
python main.py
```

La aplicación abre una interfaz con los campos:
- **Modo**: `Compare` o `Transcribe-Only`
- **Motor**: `Whisper` o `Deepgram`
- **Modelo**: según motor
- **Idioma**
- **Carpeta de audios**
- **Excel (Script)** (solo en Compare)
- **Output**

---

## Motores y modelos

### Whisper (local)

Modelos disponibles en la UI:
- `Tiny`
- `Base`
- `Small`
- `Medium` (default)
- `Large`
- `Large-v3`

Comportamiento:
- Usa **GPU** si hay CUDA; si no, usa CPU.
- Audios cortos (<15s): transcripción directa.
- Audios largos: segmentación por silencios para robustez.

### Deepgram (API)

Modelo disponible:
- `nova-3`

Comportamiento:
- Solicita la **DEEPGRAM_API_KEY** al presionar **Run**.
- Procesa audios en paralelo con workers.

Configuración de concurrencia:

```bash
# opcional (default: 4)
export DEEPGRAM_MAX_WORKERS=8
```

En Windows PowerShell:

```powershell
$env:DEEPGRAM_MAX_WORKERS = "8"
```

---

## API Key de Deepgram

Cuando el motor seleccionado es **Deepgram**, la app muestra un cuadro para pegar tu API key.

- No se ejecuta si la key está vacía.
- Puedes gestionar la concurrencia por variable `DEEPGRAM_MAX_WORKERS`.

> Recomendación: evita hardcodear keys en código o repositorio.

---

## Formato del Excel (modo Compare)

Actualmente el flujo de comparación usa estas columnas:
- `Filename` → nombre/ruta relativa del audio
- `Script` → texto esperado

Salida:
- `transcripcion`
- `coincide` (`True`, `False`, `None`)

Colores en `coincide`:
- 🟩 `True`
- 🟥 `False`
- 🟨 `None`

---

## Archivos de audio soportados

Búsqueda recursiva en la carpeta seleccionada:
- `.wav`
- `.mp3`
- `.m4a`

---

## Notas de rendimiento

- **Whisper**: mayor calidad suele implicar más VRAM/tiempo (`large`, `large-v3`).
- **Deepgram**: para lotes grandes suele rendir mejor con workers > 1 (según red y cuota API).
- Si estás limitado por hardware local, Deepgram puede reducir carga local al delegar STT en API.

---

## Estructura rápida del repo

- `main.py`: UI y orquestación principal.
- `transcribe_or_compare.py`: motores STT, transcripción y comparación Excel.
- `lib_installer.py`: utilidades para instalación/verificación de entorno.

