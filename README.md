# AsRec Reviewer

Herramienta de **transcripción de audios con Whisper** y exportación a Excel, con dos modos:

- `compare`: transcribe y compara contra un guion en Excel.
- `transcribe-only`: solo transcribe y genera un Excel nuevo.

> Estado actual: **funcional** (sin cambios de funcionalidad en esta limpieza).

---

## Qué hace hoy

- Recorre una carpeta de audios (`.wav`, `.mp3`, `.m4a`).
- Transcribe cada archivo con Whisper local (CPU o CUDA).
- Permite forzar idioma (`--language es`, `--language en`, etc.).
- En modo comparación:
  - lee un Excel de entrada,
  - compara texto esperado vs transcripción con normalización (minúsculas, sin tildes, sin puntuación),
  - marca resultados en Excel con colores (verde/rojo/amarillo),
  - resalta diferencias de manera simple usando marcadores `*palabra*`.
- En modo solo transcripción:
  - genera un Excel con columnas `audio_file` y `transcripcion`.

---

## Requisitos

- Python 3.10+
- FFmpeg instalado en el sistema (requerido por Whisper)
- Dependencias Python:
  - `openai-whisper`
  - `torch`
  - `pandas`
  - `openpyxl`

Ejemplo de instalación rápida:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install openai-whisper torch pandas openpyxl
```

---

## Uso

### 1) Modo comparación

```bash
python main.py \
  --mode compare \
  --audio-folder ./audios \
  --excel ./guion.xlsx \
  --audio-column audio_file \
  --expected-column guion \
  --output ./resultado_comparacion.xlsx \
  --model-size medium \
  --language es
```

### 2) Modo solo transcripción

```bash
python main.py \
  --mode transcribe-only \
  --audio-folder ./audios \
  --output ./solo_transcripciones.xlsx \
  --model-size medium \
  --language es
```

### 3) Modo interactivo

Si ejecutas sin argumentos, entra en modo interactivo y te va pidiendo los datos.

```bash
python main.py
```

---

## Estructura esperada (mínima)

```text
.
├── main.py
├── README.md
└── (carpetas de audios y excels de trabajo)
```

---

## Pendientes de limpieza (sin tocar funcionalidad todavía)

Checklist sugerido para próximos commits pequeños:

- [ ] **Empaquetar proyecto**: mover script a `src/` y agregar `pyproject.toml`.
- [ ] **`requirements.txt` / lockfile** para reproducibilidad.
- [ ] **Separar lógica por módulos** (`io_excel.py`, `transcriber.py`, `compare.py`, etc.).
- [ ] **Logging estructurado** en lugar de `print`.
- [ ] **Tests unitarios** para normalización, matching y diferencias.
- [ ] **Validaciones de entrada** más claras (rutas, columnas, extensiones).
- [ ] **Optimización de escritura Excel** (guardar workbook una sola vez al final).
- [ ] **Corregir flujo de retorno en comparación** (evitar salida temprana dentro del loop).
- [ ] **Documentar manejo de errores** y casos de `None`/celdas vacías.
- [ ] **Agregar ejemplos de datos** (mini carpeta `examples/`).

> Nota: la idea de esta fase es dejar todo documentado y versionado antes de refactorizar.

---

## Sugerencia de estrategia para subir “en limpio”

Haz commits cortos, cada uno con un objetivo único. Ejemplo:

1. `docs: agrega README funcional y roadmap`
2. `chore: agrega requirements y .gitignore`
3. `test: agrega pruebas de normalize_text y match`
4. `refactor: separa módulos sin cambiar comportamiento`

---

## Cómo hacer commits desde aquí (flujo recomendado)

```bash
# 1) Ver cambios
git status

# 2) Revisar diff
git diff

# 3) Agregar archivos concretos
git add README.md

# 4) Commit con mensaje claro
git commit -m "docs: actualiza README con estado y pendientes"

# 5) Ver historial
git log --oneline -n 5

# 6) Subir rama
git push origin <tu-rama>
```

Tips rápidos:

- Usa prefijos en el commit: `docs:`, `fix:`, `refactor:`, `test:`, `chore:`.
- Evita mezclar docs + refactor + fixes en un solo commit.
- Si el cambio es grande, separa en varios commits atómicos.

---

## Próximo paso recomendado

Primero deja trazabilidad mínima:

1. README (este commit).
2. `requirements.txt`.
3. `.gitignore` (venv, caches, outputs de Excel temporales).

Con eso ya puedes iterar mejoras sin perder orden de cambios.
