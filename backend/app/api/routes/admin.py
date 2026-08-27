import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.urls import audio_url
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.generation import Generation
from app.models.user import User
from app.models.voice import Voice, VoiceStatus
from app.schemas.user import AdminUsersOut, UserOut
from pydantic import BaseModel


class UserStatusUpdate(BaseModel):
    is_active: bool


from app.schemas.voice import AdminVoiceUpdate, VoiceOut
from app.services import audio_utils
from app.services.storage import storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


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


# ---- Users ------------------------------------------------------------

@router.get("/users", response_model=AdminUsersOut)
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return AdminUsersOut(
        users=[UserOut.model_validate(u) for u in users], total=len(users)
    )


@router.patch("/users/{user_id}/status")
def set_user_status(
    user_id: int, payload: UserStatusUpdate, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = payload.is_active
    db.commit()
    return {"ok": True, "is_active": user.is_active}


# ---- Public library voices -------------------------------------------

@router.post("/voices", response_model=VoiceOut, status_code=201)
def add_public_voice(
    file: UploadFile = File(...),
    name: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    if not name.strip():
        raise HTTPException(status_code=422, detail="Voice name is required")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if not audio_utils.allowed_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Use wav, mp3, m4a, webm, ogg, opus or flac.",
        )

    rel_sample, _ = storage.save_voice_sample(data, file.filename)
    voice = Voice(
        name=name.strip()[:120],
        description=description.strip() or None,
        kind="public",
        status=VoiceStatus.PUBLIC,
        audio_sample_path=rel_sample,
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.get("/voices", response_model=list[VoiceOut])
def admin_voices(db: Session = Depends(get_db)):
    voices = db.query(Voice).order_by(Voice.created_at.desc()).all()
    return [_voice_out(v) for v in voices]


@router.patch("/voices/{voice_id}", response_model=VoiceOut)
def update_voice(
    voice_id: int,
    payload: AdminVoiceUpdate = ...,
    db: Session = Depends(get_db),
):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    if payload.name is not None:
        voice.name = payload.name.strip()[:120] or voice.name
    if payload.description is not None:
        voice.description = payload.description.strip() or None
    if payload.status is not None:
        if payload.status not in {
            VoiceStatus.PUBLIC, VoiceStatus.DISABLED,
            VoiceStatus.PRIVATE, VoiceStatus.DELETED,
        }:
            raise HTTPException(status_code=422, detail="Invalid status")
        voice.status = payload.status

    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.delete("/voices/{voice_id}", status_code=200)
def delete_voice(voice_id: int, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    storage.remove(voice.audio_sample_path)
    storage.remove(voice.preview_path)
    voice.status = VoiceStatus.DELETED
    db.commit()
    return {"status": "deleted"}


# ---- Publish user-created voices -------------------------------------

@router.post("/voices/{voice_id}/publish", response_model=VoiceOut)
def publish_user_voice(voice_id: int, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice or voice.status == VoiceStatus.DELETED:
        raise HTTPException(status_code=404, detail="Voice not found")
    if voice.kind != "clone":
        raise HTTPException(status_code=400, detail="Only user-created voices can be published")

    voice.status = VoiceStatus.PUBLIC
    voice.promoted_to_public = True
    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.post("/voices/{voice_id}/unpublish", response_model=VoiceOut)
def unpublish(voice_id: int, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    voice.status = VoiceStatus.PRIVATE if voice.kind == "clone" else VoiceStatus.DISABLED
    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


# ---- User-created voices ----------------------------------------------

@router.get("/user-voices", response_model=list[VoiceOut])
def user_voices(db: Session = Depends(get_db)):
    voices = (
        db.query(Voice)
        .filter(Voice.kind == "clone", Voice.status != VoiceStatus.DELETED)
        .order_by(Voice.created_at.desc())
        .all()
    )
    return [_voice_out(v) for v in voices]


# ---- Generations ------------------------------------------------------

@router.get("/generations", response_model=list[dict])
def all_generations(db: Session = Depends(get_db)):
    gens = (
        db.query(Generation).order_by(Generation.created_at.desc()).limit(500).all()
    )
    users = {
        u.id: u for u in db.query(User).filter(
            User.id.in_({g.created_by_id for g in gens})
        ).all()
    } if gens else {}
    out = []
    for g in gens:
        u = users.get(g.created_by_id)
        out.append(
            {
                "id": g.id,
                "text": g.text,
                "voice_id": g.voice_id,
                "voice_name": g.voice_name,
                "audio_url": audio_url(g.audio_path),
                "created_at": g.created_at,
                "user": {"id": u.id, "email": u.email} if u else None,
            }
        )
    return out