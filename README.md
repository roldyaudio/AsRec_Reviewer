# AsRec Reviewer (base)

Script para:
1. Transcribir audios (Whisper, GPU con CUDA si está disponible).
2. Opción A: comparar transcripción vs guion esperado en Excel.
3. Opción B: solo transcribir y exportar a un nuevo Excel.
4. En modo comparación, generar colores:
   - Verde: coincide
   - Rojo: no coincide
   - Amarillo: no evaluable (vacíos o faltantes)

## Requisitos

```bash
pip install openai-whisper torch pandas openpyxl
```

## Modos de ejecución

### 1) Solo transcribir a un Excel nuevo

```bash
python transcribe_compare.py \
  --mode transcribe-only \
  --audio-folder ./audios \
  --output ./solo_transcripciones.xlsx \
  --model-size medium \
  --language es
```

Genera un Excel con columnas:
- `audio_file`
- `transcripcion`

### 2) Transcribir + comparar contra Excel de guion

## Formato esperado del Excel (modo compare)

Debe tener al menos estas columnas (configurables por parámetro):
- `audio_file`: nombre o ruta relativa del audio (ej: `carpeta1/audio_001.wav`)
- `guion`: texto esperado

## Ejecución (modo compare)

```bash
python transcribe_compare.py \
  --mode compare \
  --audio-folder ./audios \
  --excel ./guiones.xlsx \
  --audio-column audio_file \
  --expected-column guion \
  --output ./resultado_comparacion.xlsx \
  --model-size medium \
  --language es
```

Si quieres autodetección de idioma, envía `--language ""`.

## Próximas mejoras recomendadas

- Medir similitud con fuzzy matching (no solo exact/contains).
- Guardar score de confianza por fila.
- Añadir cache de transcripciones para no reprocesar audios ya vistos.
- Exportar reporte de errores en CSV para revisión rápida.
