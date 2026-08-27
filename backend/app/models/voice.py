from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VoiceStatus:
    PROCESSING = "processing"
    PRIVATE = "private"
    PUBLIC = "public"
    DISABLED = "disabled"
    DELETED = "deleted"


class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "public" (admin library) or "clone" (user-created)
    kind: Mapped[str] = mapped_column(String(20), default="public", index=True)

    # "public" | "private" | "processing" | "disabled" | "deleted"
    status: Mapped[str] = mapped_column(String(20), default="public", index=True)

    # Reference audio used to synthesize/instantiate this voice
    audio_sample_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Preview audio (usually a small generated sample)
    preview_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Provider voice id (ElevenLabs) when available
    provider_voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # True when this is a clone created by a user that was later published by an admin
    promoted_to_public: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    created_by: Mapped["User | None"] = relationship(back_populates="voices")

    def __repr__(self):
        return f"<Voice {self.id} {self.name!r} [{self.status}]>"