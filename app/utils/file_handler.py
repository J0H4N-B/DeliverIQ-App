"""
app/utils/file_handler.py — Manejo seguro de archivos CSV
"""

import io
import logging
import os
import uuid

import pandas as pd
from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    pass


# ══════════════════════════════════════════════════════════════
# FIRMAS DE BYTES MÁGICOS (archivos disfrazados de CSV)
# ══════════════════════════════════════════════════════════════

_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x50\x4B\x03\x04", "Excel/ZIP"),          # .xlsx, .zip
    (b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", "Excel 97-2003"),  # .xls
    (b"\x25\x50\x44\x46", "PDF"),                 # %PDF
    (b"\x89\x50\x4E\x47", "PNG"),
    (b"\xFF\xD8\xFF", "JPEG"),
    (b"\x47\x49\x46\x38", "GIF"),
]


def _detect_magic_bytes(raw: bytes) -> str | None:
    """Devuelve el tipo detectado si el contenido NO es texto plano, o None si es seguro."""
    for signature, file_type in _MAGIC_SIGNATURES:
        if raw.startswith(signature):
            return file_type
    return None


# ══════════════════════════════════════════════════════════════
# GUARDADO SEGURO
# ══════════════════════════════════════════════════════════════

def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_uploaded_file(file: FileStorage) -> str:
    """
    Valida y guarda el archivo CSV de forma segura.

    Orden de validaciones:
      1. Presencia del archivo
      2. Extensión permitida
      3. Lectura en memoria (antes de tocar disco)
      4. Contenido no vacío (0 bytes)
      5. Bytes mágicos (detecta binarios disfrazados de CSV)
      6. Límite de tamaño configurable vía MAX_UPLOAD_BYTES en config
      7. Escritura en disco con nombre sanitizado + UUID
    """
    if not file or not file.filename:
        raise FileValidationError("No se recibió ningún archivo.")

    if not allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "sin extensión"
        raise FileValidationError(
            f"Formato '{ext}' no permitido. El archivo debe ser .csv"
        )

    raw = file.read()

    if len(raw) == 0:
        raise FileValidationError("El archivo está vacío (0 bytes).")

    detected_type = _detect_magic_bytes(raw)
    if detected_type:
        raise FileValidationError(
            f"El archivo parece ser de tipo {detected_type}, no un CSV válido. "
            "Asegúrate de exportar los datos como texto CSV."
        )

    max_bytes = current_app.config.get("MAX_UPLOAD_BYTES", 52_428_800)  # 50 MB por defecto
    if len(raw) > max_bytes:
        mb = max_bytes // 1_048_576
        raise FileValidationError(
            f"El archivo supera el límite de {mb} MB permitido."
        )

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    filepath = os.path.join(upload_folder, unique_name)

    with open(filepath, "wb") as fout:
        fout.write(raw)

    logger.info("Archivo guardado: %s (%d bytes)", unique_name, len(raw))
    return filepath


# ══════════════════════════════════════════════════════════════
# LECTURA SEGURA CSV
# ══════════════════════════════════════════════════════════════

_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")
_SEPARATORS = (",", ";", "\t", "|")


def _try_read_csv(raw: bytes, encoding: str, sep: str, max_rows: int) -> pd.DataFrame | None:
    """Intenta parsear el CSV con un encoding y separador dados. Devuelve None si falla."""
    try:
        return pd.read_csv(
            io.BytesIO(raw),
            encoding=encoding,
            sep=sep,
            nrows=max_rows,
            engine="python",
        )
    except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None
    except Exception:
        return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df


def read_csv_safe(filepath: str, max_rows: int = 50_000) -> pd.DataFrame:
    """
    Lee el CSV con detección automática de encoding y separador.

    Estrategia:
      - Prueba encodings: utf-8-sig → utf-8 → latin-1
      - Para cada encoding, prueba separadores: , ; \\t |
      - Valida que haya al menos 1 fila de datos (no solo encabezados)
      - Advierte si solo se detecta 1 columna (posible separador incorrecto)
      - Normaliza nombres de columnas
    """
    if not os.path.exists(filepath):
        raise FileValidationError("El archivo no se encontró en el servidor.")

    with open(filepath, "rb") as f:
        raw = f.read()

    if len(raw) == 0:
        raise FileValidationError("El archivo está vacío.")

    df: pd.DataFrame | None = None
    used_sep: str | None = None

    for encoding in _ENCODINGS:
        for sep in _SEPARATORS:
            candidate = _try_read_csv(raw, encoding, sep, max_rows)
            if candidate is not None and not candidate.empty and len(candidate.columns) > 1:
                df = candidate
                used_sep = sep
                logger.debug("CSV leído con encoding=%s sep=%r", encoding, sep)
                break
        if df is not None:
            break

    # Si ningún separador dio >1 columna, intenta igualmente con la primera combinación
    # válida aunque tenga 1 sola columna (para darle un mensaje de advertencia útil)
    if df is None:
        for encoding in _ENCODINGS:
            candidate = _try_read_csv(raw, encoding, ",", max_rows)
            if candidate is not None:
                df = candidate
                used_sep = ","
                break

    if df is None:
        raise FileValidationError(
            "No se pudo leer el archivo. Verifica que sea un CSV de texto plano "
            "con codificación UTF-8 o Latin-1."
        )

    try:
        if df.empty:
            raise pd.errors.EmptyDataError
    except pd.errors.EmptyDataError:
        raise FileValidationError("El CSV no contiene datos (solo encabezados o está vacío).")

    if len(df) == 0:
        raise FileValidationError(
            "El CSV tiene encabezados pero ninguna fila de datos."
        )

    if len(df.columns) == 1:
        sep_display = {"," : "coma", ";" : "punto y coma", "\t": "tabulador", "|": "pipe"}
        detected = sep_display.get(used_sep or "", repr(used_sep))
        logger.warning(
            "CSV con una sola columna detectada (separador usado: %r). "
            "Es posible que el separador real sea distinto.",
            used_sep,
        )
        raise FileValidationError(
            f"Solo se detectó 1 columna usando '{detected}' como separador. "
            "Si tu archivo usa punto y coma, tabulador u otro separador, "
            "asegúrate de exportarlo correctamente desde tu herramienta."
        )

    df = _normalize_columns(df)
    logger.info("CSV cargado: %d filas × %d columnas (sep=%r)", len(df), len(df.columns), used_sep)
    return df


# ══════════════════════════════════════════════════════════════
# LIMPIEZA DE UPLOADS ANTIGUOS
# ══════════════════════════════════════════════════════════════

def cleanup_old_uploads(upload_folder: str, max_files: int = 50) -> None:
    """
    Elimina los uploads más antiguos cuando se supera max_files.
    Usa mtime (fecha de modificación) para ordenar, más confiable que ctime.
    Loguea cada eliminación y los errores que puedan ocurrir.
    """
    try:
        all_files = [
            os.path.join(upload_folder, fname)
            for fname in os.listdir(upload_folder)
            if os.path.isfile(os.path.join(upload_folder, fname))
        ]
    except OSError as exc:
        logger.error("No se pudo leer la carpeta de uploads '%s': %s", upload_folder, exc)
        return

    all_files.sort(key=os.path.getmtime)

    while len(all_files) > max_files:
        oldest = all_files.pop(0)
        try:
            os.remove(oldest)
            logger.info("Archivo de upload eliminado (cuota): %s", oldest)
        except OSError as exc:
            logger.error("No se pudo eliminar '%s': %s", oldest, exc)
