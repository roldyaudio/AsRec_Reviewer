# AsRec Reviewer

Herramienta de **Speech-to-Text (STT)** con interfaz gráfica (PySide6) para:

1. **Compare**: transcribir audios y compararlos contra un Excel de referencia.
2. **Transcribe-Only**: transcribir audios y exportar resultados a un Excel nuevo.

## Novedades principales

- ✅ **Motor seleccionable**:
  - **Whisper local** (CPU/GPU).
  - **Deepgram API** (modelo `nova-3`).
- ✅ **Campo de Glosario en UI** para Deepgram con carga de `keyterms` + `variants` desde Excel.
- ✅ **Paralelismo con workers** para Deepgram usando `ThreadPoolExecutor`.
- ✅ **Ingreso de API Key de Deepgram** desde la UI (prompt seguro tipo password).
- ✅ Soporte de modelo Whisper `large-v3`.
- ✅ Detección recursiva de audio (`.wav`, `.mp3`, `.m4a`).
- ✅ Métricas reales de calidad STT en Excel (`wer_pct`, `cer_pct`, `quality`) con resaltado verde/amarillo/rojo.
- ✅ Sección **QA** opcional para generar un proyecto de REAPER (`.rpp`) con tracks separados por `quality`.

---

## Requisitos

- Python 3.10+
- FFmpeg en `PATH` solo si usarás **Whisper local** (`pydub` lo requiere).

Instalación rápida:

```bash
pip install -r requirements.txt
```

Dependencias principales para el flujo por defecto (**Deepgram**):
- `PySide6`
- `deepgram-sdk>=3.11.0,<4.0.0`
- `pandas`
- `openpyxl`
- `jiwer`

> Nota Deepgram: este proyecto usa la API del SDK Python v3 (`PrerecordedOptions` + `listen.rest.v("1").transcribe_file`). Mantén `deepgram-sdk` en `>=3.11.0,<4.0.0`; las versiones mayores cambiaron la superficie del SDK y pueden romper imports/API usados por esta app.

Dependencias locales opcionales para **Whisper**:
- `openai-whisper`
- `torch`
- `pydub`

> Nota: la GUI arranca con **Deepgram** como motor por defecto y el instalador automático omite las dependencias locales de Whisper hasta que selecciones ese motor, para evitar instalar PyTorch/CUDA en equipos que no lo necesitan. Whisper usa CUDA automáticamente si `torch.cuda.is_available()` es verdadero.

### Instalador automático de la GUI

Al ejecutar `python main.py`, la app usa `lib_installer.py` sobre la carpeta real del proyecto (`main.py`), no sobre una ruta fija como `C:/Apps/AsRec_Reviewer`. Por eso los mensajes del instalador reflejan el `requirements.txt` actualizado de esta copia del repo: debe revisar `jiwer` y ya no debe reportar `RapidFuzz` si ese paquete no está en el archivo actual.

Por defecto, el instalador omite dependencias locales pesadas de Whisper (`openai-whisper`, `pydub`, `torch`, `torchvision`, `torchaudio`) para evitar instalaciones innecesarias cuando se trabaja con Deepgram. Si quieres preparar Whisper manualmente desde el instalador, define:

```bash
export INSTALL_WHISPER_LOCAL=1
python lib_installer.py
```

En Windows PowerShell:

```powershell
$env:INSTALL_WHISPER_LOCAL = "1"
python lib_installer.py
```

---

## Ejecución

```bash
python main.py
```

La aplicación abre una interfaz organizada en secciones:

- **Engine and Language**:
  - **Mode**: `Compare` o `Transcribe-Only`
  - **Engine**: `Deepgram` por defecto, o `Whisper` si necesitas transcripción local
  - **Model**: según motor
  - **Language**
- **Paths**:
  - **Audio file folder**
  - **Script** (solo en Compare)
  - **Glossary** (habilitado cuando `Engine = Deepgram`, tanto en Compare como en Transcribe-Only)
  - **Output file**
- **QA**:
  - **Generate QA Reaper project**: disponible en Compare para crear un `.rpp` junto al Excel de salida.

---

## Motores y modelos

### Whisper (local)

Modelos disponibles en la UI:
- `Tiny`
- `Base`
- `Small`
- `Medium` (default de Whisper cuando se selecciona ese motor)
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
- Si se carga un glosario, envía `keyterms` a Deepgram (Nova-3).
- Muestra en consola el conteo de keyterms reales y nivel recomendado:
  - 🟢 ideal: 10–50
  - 🟡 ok: 50–120
  - 🔴 riesgo: 120+

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
- Puedes cargar un glosario opcional en formato Excel para priorizar términos.

> Recomendación: evita hardcodear keys en código o repositorio.

---

## Formato del Excel (modo Compare)

Actualmente el flujo de comparación usa estas columnas:
- `Filename` → nombre/ruta relativa del audio
- `Script` → texto esperado

Salida:
- `transcripcion`
- `wer_pct` → Word Error Rate en porcentaje.
- `cer_pct` → Character Error Rate en porcentaje.
- `quality` → clasificación de calidad (`excellent`, `acceptable`, `poor`, `not_evaluated`).

Normalización de WER:
- convierte a minúsculas;
- elimina puntuación;
- limpia símbolos/puntuación unicode no alfanuméricos;
- compacta espacios repetidos;
- recorta espacios al inicio/final.

Normalización de CER:
- recorta espacios al inicio/final.

Idiomas sin separación por espacios:
- Para japonés, chino, coreano y tailandés, el sistema omite WER porque no es una métrica significativa en esos idiomas.
- En esos casos `wer_pct` queda vacío y se calcula `cer_pct`.

Colores de calidad:
- 🟩 `excellent` = transcripción excelente.
- 🟨 `acceptable` / `not_evaluated` = calidad media o fila no evaluable por texto vacío.
- 🟥 `poor` = transcripción pobre.

Los umbrales se centralizan en `transcribe_or_compare.py`:
- WER excelente: `<= 5%`; aceptable: `<= 15%`.
- CER excelente: `<= 2%`; aceptable: `<= 8%`.

---


## QA Reaper project

En modo **Compare**, el checkbox **Generate QA Reaper project** crea un archivo `.rpp` junto al Excel de salida, usando el mismo nombre con sufijo `_qa.rpp`. Por ejemplo, si el Excel se guarda como `resultado.xlsx`, el proyecto se guarda como `resultado_qa.rpp`.

El proyecto de REAPER contiene un track por cada valor de `quality` soportado por el reporte:

- `excellent`
- `acceptable`
- `not_evaluated`
- `poor`

Los items se insertan siguiendo el orden del Script/report en una línea de tiempo global: cada clip cae en el track de su `quality`, pero el siguiente clip comienza después del anterior más la separación configurada, evitando overlapping entre tracks. El generador intenta resolver cada audio contra la carpeta **Audio file folder** usando primero la ruta relativa del reporte y luego el nombre de archivo.

Los colores suaves de QA se centralizan como variables globales en `rpp_qa.py` y se reutilizan también para pintar el Excel, manteniendo la misma paleta: verde para `excellent`, amarillo para `acceptable` / `not_evaluated` y rojo para `poor`.

## Glosario Deepgram (Excel)

El campo **Glosario** en la GUI se usa para cargar un Excel con términos priorizados para Deepgram.

### Cuándo se habilita el campo Glosario

- ✅ Habilitado solo cuando:
  - `Motor = Deepgram`
- ❌ Deshabilitado (oscurecido) en:
  - cualquier modo con `Motor = Whisper`

### Columnas obligatorias del Excel de glosario

Debes usar exactamente estas columnas:

| term | boost | variants | enabled | notes |
|---|---:|---|---|---|
| Jedi | 1.2 | yedai,yedi | TRUE | |
| Hola | 0 | | FALSE | |
| Tatooine | 1.5 | tatooin,tatuin | TRUE | |
| Ubisoft | 1.2 | yubisoft | TRUE | |

### Reglas de carga

- Solo se incluyen filas donde `enabled` sea verdadero (`TRUE`, `true`, `1`, `yes`, `sí`, etc.).
- `term` vacío no se incluye.
- `variants` acepta variantes separadas por coma.
- `boost` se conserva como columna de plantilla, pero **Nova-3 no usa boost** (Deepgram requiere `keyterm`).

### Resultado esperado que se envía a Deepgram (Nova-3)

Ejemplo (según las filas habilitadas):

```text
[
  "Jedi",
  "yedai",
  "yedi",
  "Tatooine",
  "tatooin",
  "tatuin"
]
```

> Si no cargas glosario, o si no hay filas habilitadas, Deepgram se ejecuta sin keyterms adicionales.

### Uso por línea de comandos (opcional)

```bash
python transcribe_or_compare.py --engine deepgram --glossary ruta/al/glosario.xlsx
```

---

## Archivos de audio soportados

Búsqueda recursiva en la carpeta seleccionada:
- `.wav`
- `.mp3`
- `.m4a`

---

## Notas de rendimiento

- **Deepgram** es el motor por defecto para evitar instalar dependencias locales pesadas en equipos sin GPU.
- **Whisper**: mayor calidad suele implicar más VRAM/tiempo (`large`, `large-v3`). Al seleccionar Whisper desde la GUI, se instalan las dependencias locales necesarias.
- **Deepgram**: para lotes grandes suele rendir mejor con workers > 1 (según red y cuota API).
- Si estás limitado por hardware local, Deepgram puede reducir carga local al delegar STT en API.

---

## Estructura rápida del repo

- `main.py`: UI y orquestación principal.
- `transcribe_or_compare.py`: motores STT, transcripción y comparación Excel.
- `lib_installer.py`: utilidades para instalación/verificación de entorno.
