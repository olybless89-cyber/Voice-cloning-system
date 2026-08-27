from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VoiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class VoiceOut(VoiceBase):
    id: int
    kind: str
    status: str
    audio_url: str | None = None
    preview_url: str | None = None
    created_at: datetime
    owner: dict | None = None  # {id, email} when it's a user-created voice

    class Config:
        from_attributes = True


class VoiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: Literal["public", "disabled", "private", "deleted"] | None = None


class CloneResult(BaseModel):
    id: int
    status: str
    message: str


class AdminVoiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: Literal["public", "disabled", "private", "deleted"] | None = None


class TreeItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    kind: str
    status: str
    preview_url: str | None = None


class VoiceTree(BaseModel):
    library: list[TreeItem]
    mine: list[TreeItem]