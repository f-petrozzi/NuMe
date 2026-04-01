from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AIRateCounter(Base):
    __tablename__ = "ai_rate_counters"

    bucket_key: Mapped[str] = mapped_column(Text, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
