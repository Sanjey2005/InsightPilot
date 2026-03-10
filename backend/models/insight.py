import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, ForeignKey("runs.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    # trend | anomaly | segment | kpi
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    sql_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-encoded Recharts chart config from viz agent
    chart_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-encoded list of data rows powering the chart (capped at 50 rows)
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kpi_column: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # low | medium | high
    severity: Mapped[str] = mapped_column(String, default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
