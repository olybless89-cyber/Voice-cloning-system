import json
import math
import shutil
import struct
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


# ---------------------------------------------------------------------------
# Zero-key "proximity cloning"
# ---------------------------------------------------------------------------
# True per-speaker voice cloning needs a trained model (ElevenLabs, Coqui XTTS,
# ...) and is only available when ELEVENLABS_API_KEY is set. Without a key we
# approximate it: decode the recorded sample, measure the speaker's average
# pitch, then push a stock neural voice toward that acoustic profile (pitch
# shift) so the output is per-recording and actually uses the sample, instead
# of silently falling back to a generic voice chosen by the name.

RATE = 24000  # analysis sample rate for F0 estimation


def decode_to_pcm(path: Path, rate: int = RATE) -> bytes | None:
    """Decode any audio file to mono 16-bit PCM using ffmpeg, or None on failure."""
    if not ffmpeg_available():
        return None
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", str(path),
                "-ac", "1", "-ar", str(rate), "-f", "s16le", "-acodec", "pcm_s16le",
                "-",  # stdout
            ],
            capture_output=True, timeout=120,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        return proc.stdout
    except Exception:
        return None


def estimate_f0(pcm: bytes, rate: int = RATE) -> float:
    """Estimate the average fundamental frequency (Hz) from mono 16-bit PCM via
    autocorrelation. Returns 0.0 when the signal is silent or unvoiced."""
    if not pcm or len(pcm) < rate // 2:
        return 0.0
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    hop = 4
    down = samples[::hop]
    win = rate // 2  # 0.5s of analysis at RATE
    down_rate = rate // hop  # effective rate after simple decimation

    fund = 0.0
    weight = 0
    min_period = down_rate / 420   # ~420 Hz upper bound
    max_period = down_rate / 65    # ~65 Hz lower bound
    win_ds = win // hop
    for start in range(0, len(down) - win_ds, win_ds // 2):
        block = down[start:start + win_ds]
        n = len(block)
        rms = math.sqrt(sum(s * s for s in block) / n) if n else 0.0
        if rms < 0.25 * 32767:  # skip near-silent / quiet frames
            continue
        lo = max(int(min_period), 1)
        hi = min(int(max_period) + 1, n - 1)
        scores = {}
        for lag in range(lo, hi):
            s = 0.0
            for i in range(n - lag):
                s += block[i] * block[i + lag]
            # Normalised autocorrelation: s(lag) / s(0) gives a value in [-1, 1].
            denominator = (
                sum(block[i] * block[i] for i in range(n - lag)) or 1.0
            )
            scores[lag] = s / denominator
        if not scores:
            continue
        peak = max(scores.values())
        if peak <= 0.35:  # not voiced / too quiet correlation-wise
            continue
        # Prefer the smallest lag within 90% of the max correlation. The
        # autocorrelation of a periodic signal peaks at every multiple of the
        # period, so this picks the TRUE (shortest) period instead of an
        # octave-down subharmonic.
        best_lag = min(
            lag for lag, sc in scores.items() if sc >= 0.9 * peak
        )
        fund += down_rate / best_lag
        weight += 1
    return (fund / weight) if weight else 0.0


def resample_pcm(pcm: bytes, rate: int = RATE) -> bytes:
    """Simple linear-interpolation resampling to a target sample rate."""
    if rate == RATE:
        return pcm
    src = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    if len(src) < 2:
        return pcm
    ratio = RATE / rate
    out_count = int(len(src) / ratio)
    out = bytearray()
    for i in range(out_count):
        pos = i * ratio
        idx = int(pos)
        frac = pos - idx
        nxt = min(idx + 1, len(src) - 1)
        val = int(src[idx] * (1 - frac) + src[nxt] * frac)
        out += struct.pack("<h", max(-32768, min(32767, val)))
    return bytes(out)


def pitch_and_rate(path: Path) -> tuple[float, float]:
    """Return (pitch_hz, speed_scale). speed is a placeholder (1.0)."""
    pcm = decode_to_pcm(path)
    if not pcm:
        return 0.0, 1.0
    return round(estimate_f0(pcm), 1), 1.0


def apply_proximity_pitch(source_pcm: bytes, target_f0: float, src_f0: float | None = None, rate: int = RATE) -> bytes:
    """Resample ``source_pcm`` so its average pitch becomes ``target_f0``."""
    if target_f0 <= 0:
        return source_pcm
    s0 = src_f0 if src_f0 and src_f0 > 0 else estimate_f0(source_pcm, rate)
    if s0 <= 0:
        return source_pcm
    ratio = max(0.7, min(1.6, target_f0 / s0))
    try:
        return resample_pcm(source_pcm, int(rate / ratio))
    except Exception:
        return source_pcm


def pcm_to_mp3(pcm: bytes, path: Path, rate: int = RATE) -> bool:
    """Encode raw 16-bit PCM mono to MP3 at ``path`` using ffmpeg."""
    if not ffmpeg_available():
        return False
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1",
                "-i", "-", "-ar", "44100", "-b:a", "192k", "-y", str(path),
            ],
            input=pcm, capture_output=True, timeout=120,
        )
        return proc.returncode == 0 and path.stat().st_size > 0
    except Exception:
        return False


def proximity_clone(source_bytes: bytes, suffix: str, source_sample_path: Path) -> bytes:
    """Best-effort zero-key proximity clone: pitch-shift generated speech toward
    the recording's average pitch. Returns input unchanged if analysis fails, so
    output is never worse than the pre-existing fallback."""
    sample_pitch, _ = pitch_and_rate(source_sample_path)
    if sample_pitch <= 0:
        return source_bytes
    with tempfile.NamedTemporaryFile(suffix=suffix or ".mp3", delete=False) as tf:
        tf.write(source_bytes)
        gen_path = Path(tf.name)
    try:
        gen_pcm = decode_to_pcm(gen_path)
    finally:
        gen_path.unlink(missing_ok=True)
    if not gen_pcm:
        return source_bytes
    shifted = apply_proximity_pitch(gen_pcm, sample_pitch)
    if shifted is gen_pcm or shifted == gen_pcm:
        return source_bytes
    out_fd, out_name = tempfile.mkstemp(suffix=".mp3")
    import os
    os.close(out_fd)
    out_path = Path(out_name)
    try:
        if pcm_to_mp3(shifted, out_path):
            data = out_path.read_bytes()
            if data:
                return data
    finally:
        out_path.unlink(missing_ok=True)
    return source_bytes