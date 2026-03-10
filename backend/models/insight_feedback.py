import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class InsightFeedback(Base):
    __tablename__ = "insight_feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    insight_id: Mapped[str] = mapped_column(
        String, ForeignKey("insights.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    # thumbs_up | thumbs_down | saved
    signal: Mapped[str] = mapped_column(String, nullable=False)
    # Optional free-text note ("Share this with the team on Friday")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
