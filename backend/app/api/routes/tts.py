import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.urls import audio_url
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.generation import Generation
from app.models.user import User
from app.models.voice import Voice, VoiceStatus
from app.schemas.generation import GenerationList, GenerationOut, GenerationRequest
from app.services import audio_utils
from app.services.storage import storage
from app.services.tts_provider import TTSError, tts_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])


def _gen_out(g: Generation) -> GenerationOut:
    return GenerationOut(
        id=g.id,
        text=g.text,
        voice_id=g.voice_id,
        voice_name=g.voice_name,
        audio_url=audio_url(g.audio_path),
        duration_seconds=None,
        created_at=g.created_at,
    )


def _resolve_voice(db: Session, voice_id: int, current: User) -> Voice:
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice or voice.status == VoiceStatus.DELETED:
        raise HTTPException(status_code=404, detail="Voice not found")
    usable = voice.status == VoiceStatus.PUBLIC or (
        voice.status == VoiceStatus.PRIVATE and voice.created_by_id == current.id
    )
    if not usable:
        raise HTTPException(status_code=403, detail="This voice is not available")
    return voice


@router.post("/generate", response_model=GenerationOut, status_code=201)
def generate(
    payload: GenerationRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    voice = _resolve_voice(db, payload.voice_id, current)

    voice_ref = {
        "provider_voice_id": voice.provider_voice_id,
        "audio_sample_path": (
            str(storage.path(voice.audio_sample_path))
            if voice.audio_sample_path else None
        ),
    }

    try:
        audio_bytes, suffix = tts_provider.synthesize(payload.text, voice_ref)
    except TTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    rel, path = storage.save_generation(audio_bytes, suffix)
    duration = audio_utils.duration_or_zero(path, audio_bytes)

    gen = Generation(
        text=payload.text,
        voice_id=voice.id,
        voice_name=voice.name,
        audio_path=rel,
        created_by_id=current.id,
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)

    out = _gen_out(gen)
    out.duration_seconds = duration
    return out


@router.get("/history", response_model=GenerationList)
def history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Generation)
        .filter(Generation.created_by_id == current.id)
        .order_by(Generation.created_at.desc())
        .all()
    )
    return GenerationList(
        items=[_gen_out(g) for g in items], total=len(items)
    )


@router.delete("/{generation_id}", status_code=200)
def delete_generation(
    generation_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gen = (
        db.query(Generation)
        .filter(
            Generation.id == generation_id,
            Generation.created_by_id == current.id,
        )
        .first()
    )
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    storage.remove(gen.audio_path)
    db.delete(gen)
    db.commit()
    return {"status": "deleted"}