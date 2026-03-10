import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # "csv" | "postgres"
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    # For CSV: original filename. For Postgres: sanitised connection metadata (no password).
    storage_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # SQLite table that holds the actual data rows: upload_{user_id}_{timestamp}
    table_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Full schema profile stored as JSON (SchemaPreview)
    schema_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
