import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.services import openai_agent
from app.services.openai_agent import AgentDisabledError, AgentError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


def _enabled_or_raise() -> None:
    try:
        openai_agent.assert_configured()
    except AgentDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


class AgentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=6000)
    # Used by rewrite (tone) / translate (language) / describe (details).
    option: str | None = Field(default=None, max_length=100)
    sentences: int = Field(default=3, ge=1, le=8)


def _handle(fn, text: str, option: str | None):
    _enabled_or_raise()
    try:
        return fn(text, option) if option is not None else fn(text)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/status")
def status():
    return {
        "enabled": openai_agent.is_enabled(),
        "model": settings.openai_model if openai_agent.is_enabled() else None,
        "provider": "openai",
    }


@router.post("/rewrite")
def rewrite(payload: AgentRequest, current: User = Depends(get_current_user)):
    return {"text": _handle(openai_agent.rewrite, payload.text, payload.option or "natural")}


@router.post("/proofread")
def proofread(
    payload: AgentRequest,
    current: User = Depends(get_current_user),
):
    return {"text": _handle(openai_agent.proofread, payload.text, None)}


@router.post("/translate")
def translate(
    payload: AgentRequest,
    current: User = Depends(get_current_user),
):
    return {"text": _handle(openai_agent.translate, payload.text, payload.option or "English")}


@router.post("/summarise")
def summarise(
    payload: AgentRequest,
    current: User = Depends(get_current_user),
):
    return {"text": _handle(openai_agent.summarise, payload.text, str(payload.sentences))}


@router.post("/describe")
def describe(
    payload: AgentRequest,
    current: User = Depends(get_current_user),
):
    return {"text": _handle(openai_agent.describe_voice, payload.text, payload.option)}