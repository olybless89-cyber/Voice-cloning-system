import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.urls import audio_url
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.core.security import get_current_user
from app.models.user import User
from app.models.voice import Voice, VoiceStatus
from app.schemas.voice import CloneResult, VoiceOut, VoiceTree, TreeItem
from app.services import audio_utils
from app.services.storage import storage
from app.services.tts_provider import TTSError, tts_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voices", tags=["voices"])


def _voice_out(v: Voice) -> VoiceOut:
    return VoiceOut(
        id=v.id,
        name=v.name,
        description=v.description,
        kind=v.kind,
        status=v.status,
        audio_url=audio_url(v.audio_sample_path),
        preview_url=audio_url(v.preview_path),
        created_at=v.created_at,
        owner=(
            {"id": v.created_by.id, "email": v.created_by.email}
            if v.created_by else None
        ),
    )


@router.get("/library", response_model=list[VoiceOut])
def library(db: Session = Depends(get_db)):
    voices = (
        db.query(Voice)
        .filter(Voice.status == VoiceStatus.PUBLIC)
        .order_by(Voice.created_at.desc())
        .all()
    )
    return [_voice_out(v) for v in voices]


@router.get("/mine", response_model=list[VoiceOut])
def my_voices(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    voices = (
        db.query(Voice)
        .filter(
            Voice.created_by_id == current.id,
            Voice.status != VoiceStatus.DELETED,
        )
        .order_by(Voice.created_at.desc())
        .all()
    )
    return [_voice_out(v) for v in voices]


@router.get("/tree", response_model=VoiceTree)
def voice_tree(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Voices usable in TTS: public library + the current user's own voices."""
    public = (
        db.query(Voice)
        .filter(Voice.status == VoiceStatus.PUBLIC)
        .order_by(Voice.name.asc())
        .all()
    )
    mine = (
        db.query(Voice)
        .filter(
            Voice.created_by_id == current.id,
            Voice.status.in_([VoiceStatus.PRIVATE, VoiceStatus.PUBLIC]),
        )
        .order_by(Voice.created_at.desc())
        .all()
    )
    return VoiceTree(
        library=[
            TreeItem(
                id=v.id, name=v.name, description=v.description,
                kind=v.kind, status=v.status, preview_url=audio_url(v.preview_path),
            )
            for v in public
        ],
        mine=[
            TreeItem(
                id=v.id, name=v.name, description=v.description,
                kind=v.kind, status=v.status, preview_url=audio_url(v.preview_path),
            )
            for v in mine
        ],
    )


@router.post("/clone", response_model=CloneResult, status_code=201)
def clone_voice(
    file: UploadFile = File(...),
    name: str | None = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit(6)),
):
    """Upload a ~1 minute audio sample and create a cloned voice.

    The voice starts in 'processing' and the frontend polls /voices/mine (or a
    single voice fetch) until it leaves that state, then names it via PATCH.
    """
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if not audio_utils.allowed_extension(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Use wav, mp3, m4a, webm, ogg, opus or flac.",
        )

    # Persist the uploaded sample
    rel_sample, sample_path = storage.save_voice_sample(data, file.filename or "sample.mp3")

    # Heuristic length guidance (~1 minute suggested). Not enforced strictly.
    sample_duration = audio_utils.probe_duration(sample_path)
    if sample_duration and sample_duration < 5 and audio_utils.ffmpeg_available():
        logger.warning("Clone sample very short: %.1fs", sample_duration)

    voice = Voice(
        name=name or "My Clone",
        kind="clone",
        status=VoiceStatus.PROCESSING,
        audio_sample_path=rel_sample,
        created_by_id=current.id,
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)

    return CloneResult(id=voice.id, status=voice.status, message="Processing started")


@router.post("/clone/{voice_id}/finalize", response_model=VoiceOut)
def finalize_clone(
    voice_id: int,
    name: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the actual cloning after the sample is saved, assign the user-provided
    name, generate preview audio and mark the voice ready (private)."""
    voice = _get_owned_voice(db, voice_id, current.id)
    if voice.status != VoiceStatus.PROCESSING:
        raise HTTPException(
            status_code=409,
            detail="Voice is not in processing state",
        )

    sample_path = storage.path(voice.audio_sample_path)

    # Register the clone with the provider (or store locally in fallback mode)
    try:
        result = tts_provider.clone_voice(
            name or "My Clone",
            sample_path,
            description=voice.description,
        )
    except TTSError as exc:
        voice.status = VoiceStatus.DELETED
        db.commit()
        raise HTTPException(status_code=502, detail=f"Voice cloning failed: {exc}")

    voice.provider_voice_id = result.get("provider_voice_id")
    voice.name = (name or "My Clone").strip()[:120]
    voice.status = VoiceStatus.PRIVATE

    # Generate a playable preview
    try:
        preview_bytes, suffix = tts_provider.create_preview(voice.name, sample_path)
        rel, _ = storage.save_preview(preview_bytes, suffix)
        voice.preview_path = rel
    except TTSError as exc:
        logger.warning("Preview generation failed: %s", exc)

    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.get("/{voice_id}", response_model=VoiceOut)
def get_voice(
    voice_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice or (voice.status == VoiceStatus.DELETED):
        raise HTTPException(status_code=404, detail="Voice not found")
    # Users can view their own voices; public library voices are readable by all
    if voice.status != VoiceStatus.PUBLIC and voice.created_by_id != current.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return _voice_out(voice)


@router.delete("/{voice_id}", status_code=200)
def delete_voice(
    voice_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    voice = _get_owned_voice(db, voice_id, current.id)
    voice.status = VoiceStatus.DELETED
    db.commit()
    return {"status": "deleted"}


def _get_owned_voice(db: Session, voice_id: int, owner_id: int) -> Voice:
    voice = (
        db.query(Voice)
        .filter(
            Voice.id == voice_id,
            Voice.created_by_id == owner_id,
            Voice.status != VoiceStatus.DELETED,
        )
        .first()
    )
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    return voice