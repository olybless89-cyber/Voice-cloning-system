from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.voice import VoiceOut


class GenerationRequest(BaseModel):
    voice_id: int
    text: str = Field(min_length=1, max_length=2000)


class GenerationOut(BaseModel):
    id: int
    text: str
    voice_id: int | None = None
    voice_name: str | None = None
    audio_url: str
    created_at: datetime
    duration_seconds: float | None = None

    class Config:
        from_attributes = True


class GenerationCreate(BaseModel):
    text: str
    voice_id: int
    audio_path: str
    duration_seconds: float | None = None


class GenerationList(BaseModel):
    items: list[GenerationOut]
    total: int