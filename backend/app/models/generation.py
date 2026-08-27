from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    voice_id: Mapped[int | None] = mapped_column(
        ForeignKey("voices.id", ondelete="SET NULL"), nullable=True
    )
    voice_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    audio_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    voice: Mapped["Voice | None"] = relationship()

    def __repr__(self):
        return f"<Generation {self.id} by user {self.created_by_id}>"