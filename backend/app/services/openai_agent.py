"""OpenAI-powered agent for the "Script Studio".

A lightweight LLM helper that improves how users write text before it becomes
speech: rewrite for a chosen tone, proofread, translate, summarise, and
generate a voice description. Everything is optional — when ``OPENAI_API_KEY``
isn't configured the agent is disabled and the endpoints return a helpful 503.
"""

import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENAI_CHAT = "https://api.openai.com/v1/chat/completions"


class AgentDisabledError(Exception):
    """Raised when the OpenAI feature is used but not configured."""


class AgentError(Exception):
    """Raised when OpenAI returns a failure."""


def is_enabled() -> bool:
    return bool(settings.openai_api_key)


def assert_configured() -> None:
    if not is_enabled():
        raise AgentDisabledError(
            "Script Studio is disabled. Set OPENAI_API_KEY to enable it."
        )


def _chat(messages: list[dict], *, max_tokens: int = 700) -> str:
    return _chat_json(messages, max_tokens=max_tokens)


def _chat_json(messages: list[dict], *, max_tokens: int = 700) -> str:
    """Send a chat completion to OpenAI and return the message text."""
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.openai_model, "messages": messages, "max_tokens": max_tokens}
    with httpx.Client(timeout=60) as client:
        resp = client.post(OPENAI_CHAT, headers=headers, json=payload)
        if resp.status_code != 200:
            raise AgentError(
                f"OpenAI error {resp.status_code}: {resp.text[:200]}"
            )
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise AgentError("Unexpected OpenAI response shape") from exc


_PY_HELPER = (
    "You are the writing assistant inside a text-to-speech platform. "
    "Users type words that will be read aloud by a synthetic voice. "
)
_SYSTEMS = {
    "rewrite": (
        _PY_HELPER
        + "Rewrite the user's text for spoken delivery and the requested tone. "
        "Keep the meaning, return ONLY the rewritten text with no quotes or preamble."
    ),
    "proofread": (
        _PY_HELPER
        + "Fix grammar, punctuation, typos and awkward phrasing in the user's text. "
        "Return ONLY the corrected text."
    ),
    "translate": (
        _PY_HELPER
        + "Translate the user's text into the requested language naturally for "
        "spoken delivery. Return ONLY the translated text."
    ),
    "summarise": (
        _PY_HELPER
        + "Summarise the user's text into a short version suitable for a voiceover. "
        "Return ONLY the summary."
    ),
    "describe": (
        "You write short, evocative descriptions of AI voices. Based on the voice "
        "name and optional details, return a single sentence (max ~20 words)."
    ),
}


def _run(kind: str, text: str, extra: str | None = None) -> str:
    assert_configured()
    system = _SYSTEMS[kind]
    if extra:
        system += f"\n{extra}"
    return _chat([{"role": "system", "content": system}, {"role": "user", "content": text}])


def rewrite(text: str, tone: str = "natural") -> str:
    return _run("rewrite", text, f"Tone: {tone}.")


def proofread(text: str) -> str:
    return _run("proofread", text)


def translate(text: str, language: str = "English") -> str:
    return _run("translate", text, f"Language: {language}.")


def summarise(text: str, sentences: int = 3) -> str:
    return _run("summarise", text, f"Length: about {sentences} sentences.")


def describe_voice(name: str, extra: str | None = None) -> str:
    text = name
    if extra:
        text += f"\nDetails: {extra}"
    return _run("describe", text)


def clean_voice_name(name: str) -> str:
    """Slug-ish, single-word display name derived from an arbitrary label."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", name).strip()
    words = cleaned.split()
    return " ".join(w[:1].upper() + w[1:].lower() for w in words)[:120] or "Cloned Voice"


openai_agent = None  # singleton marker used for config checks