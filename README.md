# AsRec Reviewer

Herramienta en Python para transcribir audios con Whisper y generar reportes en Excel.

Incluye dos flujos principales:
1. **compare**: transcribe y compara contra un guion esperado en Excel.
2. **transcribe-only**: solo transcribe y exporta resultados a un Excel nuevo.

Además, el script soporta:
- Ejecución por **CLI** y también **modo interactivo** (si se ejecuta sin argumentos).
- Uso automático de **GPU (CUDA)** si está disponible, o CPU en caso contrario.
- Comparación robusta con **fuzzy matching** (`rapidfuzz`).
- Resaltado visual en Excel:
  - 🟩 Verde: coincide.
  - 🟥 Rojo: no coincide.
  - 🟨 Amarillo: no evaluable.
- Segmentación por silencios para audios largos, mejorando la robustez de transcripción.

---

## Requisitos

Instala dependencias:

```bash
pip install openai-whisper torch pandas openpyxl rapidfuzz pydub
```

> Nota: `pydub` requiere `ffmpeg` instalado en el sistema para leer/exportar varios formatos de audio.

---

## Archivos soportados

La búsqueda de audios en `--audio-folder` es recursiva y detecta:
- `.wav`
- `.mp3`
- `.m4a`

---

## Modos de uso

## 1) Modo `transcribe-only`

Transcribe todos los audios y crea un Excel con:
- `audio_file`
- `transcripcion`

Ejemplo:

```bash
python transcribe_compare.py \
  --mode transcribe-only \
  --audio-folder ./audios \
  --output ./solo_transcripciones.xlsx \
  --model-size medium \
  --language es
```

Si `--output` apunta a carpeta, se genera automáticamente `resultado.xlsx` dentro de esa carpeta.

---

## 2) Modo `compare`

Transcribe audios y compara contra un Excel de referencia.

### Formato esperado del Excel de entrada

Debe incluir al menos dos columnas (configurables):
- `audio_file`: nombre o ruta relativa del audio (ej. `carpeta1/audio_001.wav`)
- `guion`: texto esperado

### Ejemplo de ejecución

```bash
python transcribe_compare.py \
  --mode compare \
  --audio-folder ./audios \
  --excel ./guiones.xlsx \
  --audio-column audio_file \
  --expected-column guion \
  --sheet Hoja1 \
  --output ./resultado_comparacion.xlsx \
  --model-size medium \
  --language es
```

Si `--output` apunta a carpeta, se genera `resultado_comparacion.xlsx`.

Si hay diferencias, el texto transcrito puede marcar palabras no encontradas con formato `*PALABRA*` para facilitar revisión.

---

## Modo interactivo (sin argumentos)

Si ejecutas:

```bash
python transcribe_compare.py
```

el script entra en modo interactivo y te pide paso a paso:
- modo de ejecución,
- rutas de audios / Excel,
- columnas,
- hoja,
- salida,
- modelo,
- idioma.

Esto facilita usarlo con doble clic o sin recordar todos los flags.

---

## Argumentos CLI

- `--mode`: `compare` | `transcribe-only` (default: `compare`)
- `--audio-folder`: carpeta con audios
- `--excel`: Excel de entrada (solo `compare`)
- `--audio-column`: columna de audio (default: `audio_file`)
- `--expected-column`: columna de guion (default: `guion`)
- `--sheet`: hoja específica (opcional)
- `--output`: archivo o carpeta de salida
- `--model-size`: `tiny`, `base`, `small`, `medium`, `large`
- `--language`: idioma forzado (`es`, `en`, etc.) o vacío para autodetección

---

## Lógica de transcripción

- Para audios cortos (< 15s): transcripción directa.
- Para audios largos: segmentación por silencios y transcripción por chunks.
- Limpieza segura de archivos temporales por cada chunk.

---

## Resultado de comparación

En modo `compare`, el Excel de salida agrega:
- `transcripcion`
- `coincide` (`True`, `False`, `None`)

Y aplica color en la columna `coincide`:
- `True` → verde
- `False` → rojo
- `None` → amarillo

---

## Sugerencias operativas

- Usa `medium` como equilibrio entre velocidad/calidad.
- Si tienes GPU, `torch` + CUDA reduce significativamente el tiempo.
- Para lotes grandes, separa audios por carpeta y ejecuta por tandas.
