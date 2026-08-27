import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ALLOWED_AUDIO_EXT = {".webm", ".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac", ".mp4"}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def allowed_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_AUDIO_EXT


def sniff_is_audio(path: Path) -> bool:
    """Light-weight audio detection: read the extension + first bytes and, when
    ffprobe is present, ask it. Returns True when the data looks like audio."""
    if not path.exists() or path.stat().st_size == 0:
        return False

    if path.suffix.lower() == ".mp3":
        # MP3 frames start with an ID3 tag or sync bytes
        head = path.read_bytes()[:3]
        if head[:3] != b"ID3":
            # Look for a 0xFFEx sync frame within the first 64KB
            buf = path.read_bytes()[:65536]
            if not any(b == 0xFF and (buf[i + 1] if i + 1 < len(buf) else 0) & 0xE0 == 0xE0
                       for i, b in enumerate(buf[:-1])):
                return False

    if ffmpeg_available():
        try:
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-print_format", "json",
                    "-show_format", str(path),
                ],
                capture_output=True, timeout=30,
            )
            data = json.loads(probe.stdout or b"{}")
            return data.get("format", {}).get("format_name") is not None
        except Exception:
            pass
    return True


def probe_duration(path: Path) -> float:
    if not ffmpeg_available():
        return 0.0
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-show_format", str(path),
            ],
            capture_output=True, timeout=30,
        )
        data = json.loads(probe.stdout or b"{}")
        return float(data.get("format", {}).get("duration") or 0.0)
    except Exception:
        return 0.0


def estimate_audio_duration(data: bytes) -> float:
    """Approximate duration for generated audio without decoding: assume 128kbps
    MP3. Only used when ffprobe is unavailable."""
    return round((len(data) * 8) / 128_000, 2)


def to_wav(path: Path) -> Path:
    """Transcode any audio file to 44.1kHz mono WAV in a temp file (for ElevenLabs)."""
    fd, tmp_name = tempfile.mkstemp(suffix=".wav")
    import os
    os.close(fd)
    out = Path(tmp_name)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-ac", "1", "-ar", "44100", str(out)],
        capture_output=True, timeout=120, check=True,
    )
    return out


def duration_or_zero(path: Path, data: bytes) -> float:
    dur = probe_duration(path)
    if not dur:
        dur = estimate_audio_duration(data)
    return round(dur, 2)