"""
CSV ingestion service.

Responsibilities:
  1. Validate file size and parse the CSV with pandas.
  2. Sanitise column names and sample oversized datasets to 100K rows.
  3. Persist the DataFrame as a SQLite table named upload_{user_id}_{timestamp}.
  4. Profile the DataFrame and return a SchemaPreview.
"""

import io
import re
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from core.config import settings
from schemas.dataset import ColumnProfile, SchemaPreview

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_col(name: str) -> str:
    """Convert an arbitrary column header to a safe SQL identifier."""
    clean = re.sub(r"[^\w]", "_", str(name)).strip("_")
    return clean if clean else "col"


def _infer_type(series: pd.Series) -> str:
    """Map a pandas Series dtype to one of: integer | float | boolean | datetime | string."""
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"

    # Probe object columns: try to parse a sample as datetime
    probe = series.dropna().head(50)
    if len(probe) > 0:
        try:
            pd.to_datetime(probe, format="mixed", errors="raise")
            return "datetime"
        except Exception:
            pass

    return "string"


def _to_python(val: Any) -> Any:
    """Convert numpy/pandas scalars to plain Python types for JSON serialisation."""
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        return float(val)
    if isinstance(val, np.bool_):
        return bool(val)
    if isinstance(val, pd.Timestamp):
        return val.isoformat()
    if not isinstance(val, (str, int, float, bool)):
        return str(val)
    return val


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def profile_dataframe(df: pd.DataFrame, table_name: str) -> SchemaPreview:
    """Build a SchemaPreview from a (possibly already-stored) DataFrame."""
    total = len(df)
    columns: list[ColumnProfile] = []

    for col in df.columns:
        s = df[col]
        null_pct = round(s.isna().sum() / total * 100, 2) if total else 0.0
        samples = [_to_python(v) for v in s.dropna().head(3).tolist()]
        columns.append(
            ColumnProfile(
                name=col,
                inferred_type=_infer_type(s),
                null_percentage=null_pct,
                sample_values=samples,
            )
        )

    return SchemaPreview(table_name=table_name, row_count=total, columns=columns)


def ingest_csv(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> tuple[pd.DataFrame, str, SchemaPreview]:
    """
    Parse, validate, store, and profile a CSV upload.

    Returns:
        (dataframe, table_name, schema_preview)

    Raises:
        ValueError: for invalid/oversized/empty files.
    """
    # ── 1. Size gate ──────────────────────────────────────────────────────
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_csv_size_mb:
        raise ValueError(
            f"File is {size_mb:.1f} MB — exceeds the {settings.max_csv_size_mb} MB limit."
        )

    # ── 2. Parse ──────────────────────────────────────────────────────────
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    if df.empty:
        raise ValueError("Uploaded CSV is empty.")

    # ── 3. Sanitise column names ──────────────────────────────────────────
    df.columns = [_sanitize_col(c) for c in df.columns]

    # ── 4. Sample to 100K rows if needed ─────────────────────────────────
    if len(df) > 100_000:
        df = df.sample(n=100_000, random_state=42).reset_index(drop=True)

    # ── 5. Derive a stable, safe table name ───────────────────────────────
    ts = int(datetime.utcnow().timestamp())
    safe_uid = re.sub(r"[^\w]", "", user_id)[:20]
    table_name = f"upload_{safe_uid}_{ts}"

    # ── 6. Persist to SQLite ───────────────────────────────────────────────
    # Reuse the shared application engine so both the metadata session and
    # to_sql() share the same connection pool — avoids SQLite write-lock hangs.
    from core.database import engine as _engine  # noqa: PLC0415
    df.to_sql(table_name, _engine, if_exists="replace", index=False)

    # ── 7. Profile ────────────────────────────────────────────────────────
    schema = profile_dataframe(df, table_name)
    return df, table_name, schema
