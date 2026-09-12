"""Pre-generate Piper OGG full-table tracks (and phrases). Never called mid-drill."""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rdspan import config
from rdspan.db import connect, migrate

VOICE_FILES = {
    "es_ES-davefx-medium": (
        "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
    ),
}

HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
CELL_SLOTS = ("1s", "2s", "3s", "1p", "2p", "3p")


def _safe_id(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if not value or any(ch not in allowed for ch in value):
        raise ValueError(f"unsafe audio key: {value!r}")
    return value


def cell_dir(paradigm_id: str) -> Path:
    return config.audio_path() / "cells" / _safe_id(paradigm_id)


def cell_wav(paradigm_id: str, slot: str) -> Path:
    return cell_dir(paradigm_id) / f"{_safe_id(slot)}.wav"


def phrase_wav(phrase_id: str) -> Path:
    return config.audio_path() / "phrases" / f"{_safe_id(phrase_id)}.wav"


def voice_paths(voice: str | None = None) -> tuple[Path, Path]:
    name = voice or config.piper_voice()
    voices = config.audio_path() / "voices"
    return voices / f"{name}.onnx", voices / f"{name}.onnx.json"


def audio_exists(wav_path: Path) -> bool:
    ogg = wav_path.with_suffix(".ogg")
    return wav_path.is_file() or ogg.is_file()


def prefer_audio(wav_path: Path) -> Path | None:
    ogg = wav_path.with_suffix(".ogg")
    if ogg.is_file():
        return ogg
    if wav_path.is_file():
        return wav_path
    return None


def _discard_cell_clips(paradigm_id: str) -> None:
    directory = cell_dir(paradigm_id)
    for slot in CELL_SLOTS:
        for suffix in (".wav", ".ogg"):
            (directory / f"{slot}{suffix}").unlink(missing_ok=True)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"Downloading {url}", file=sys.stderr)
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)


def ensure_voice(voice: str | None = None) -> Path:
    name = voice or config.piper_voice()
    onnx, onnx_json = voice_paths(name)
    if onnx.is_file() and onnx_json.is_file():
        return onnx
    if name not in VOICE_FILES:
        raise RuntimeError(
            f"Unknown Piper voice {name}. Place {onnx.name} and {onnx.name}.json in {onnx.parent}"
        )
    model_rel, json_rel = VOICE_FILES[name]
    if not onnx.is_file():
        _download(f"{HF_BASE}/{model_rel}", onnx)
    if not onnx_json.is_file():
        _download(f"{HF_BASE}/{json_rel}", onnx_json)
    return onnx


def _synthesize_wav(voice, text: str, dest: Path, length_scale: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.wav")
    try:
        from piper import SynthesisConfig
    except ImportError:
        SynthesisConfig = None  # type: ignore[misc, assignment]
    with wave.open(str(tmp), "wb") as wav_file:
        if SynthesisConfig is not None:
            cfg = SynthesisConfig(length_scale=length_scale)
            voice.synthesize_wav(text, wav_file, syn_config=cfg)
        else:
            voice.synthesize(text, wav_file, length_scale=length_scale)
    tmp.replace(dest)


def _maybe_ogg(wav_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return
    ogg = wav_path.with_suffix(".ogg")
    if ogg.is_file() and ogg.stat().st_mtime >= wav_path.stat().st_mtime:
        return
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-c:a",
            "libvorbis",
            "-q:a",
            "4",
            str(ogg),
        ],
        check=True,
    )


def _concat_wavs(paths: list[Path], dest: Path, pause_ms: int | None = None) -> None:
    gap = config.full_audio_pause_ms() if pause_ms is None else pause_ms
    frames: list[bytes] = []
    params = None
    for i, path in enumerate(paths):
        with wave.open(str(path), "rb") as src:
            if params is None:
                params = src.getparams()
            frames.append(src.readframes(src.getnframes()))
            if i < len(paths) - 1:
                silence_frames = int(src.getframerate() * gap / 1000)
                frames.append(b"\x00\x00" * silence_frames)
    if params is None:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "wb") as out:
        out.setparams(params)
        for chunk in frames:
            out.writeframes(chunk)


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def stitch_full_ogg(paradigm_id: str, pause_ms: int | None = None) -> bool:
    """Build full.ogg from cell OGGs with a repeat-pause between forms."""
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        return False
    gap = config.full_audio_pause_ms() if pause_ms is None else pause_ms
    directory = cell_dir(paradigm_id)
    parts = [directory / f"{slot}.ogg" for slot in CELL_SLOTS]
    if not all(path.is_file() for path in parts):
        return False
    tmp = directory / "full.tmp.ogg"
    dest = directory / "full.ogg"
    inputs: list[str] = []
    filters: list[str] = []
    pause_s = gap / 1000
    for i, path in enumerate(parts):
        inputs.extend(["-i", str(path)])
        if i < len(parts) - 1:
            filters.append(f"[{i}]apad=pad_dur={pause_s:.3f}[a{i}]")
        else:
            filters.append(f"[{i}]anull[a{i}]")
    concat_in = "".join(f"[a{i}]" for i in range(len(parts)))
    filters.append(f"{concat_in}concat=n={len(parts)}:v=0:a=1[out]")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                *inputs,
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[out]",
                "-c:a",
                "libopus",
                "-b:a",
                "48k",
                str(tmp),
            ],
            check=True,
        )
        tmp.replace(dest)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False
    finally:
        tmp.unlink(missing_ok=True)


def stitch_all_full_tracks(*, pause_ms: int | None = None, workers: int = 8) -> dict[str, int]:
    root = config.audio_path() / "cells"
    if not root.is_dir():
        return {"written": 0, "skipped": 0}
    ids = sorted(path.name for path in root.iterdir() if path.is_dir())
    written = 0
    skipped = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(stitch_full_ogg, pid, pause_ms): pid for pid in ids}
        for fut in as_completed(futures):
            if fut.result():
                written += 1
            else:
                skipped += 1
    return {"written": written, "skipped": skipped}


def generate_audio(*, force: bool = False) -> dict[str, int]:
    conn = connect()
    try:
        migrate(conn)
        cells = conn.execute(
            "SELECT paradigm_id, slot, tts_text FROM paradigm_cells ORDER BY paradigm_id, id"
        ).fetchall()
        phrases = conn.execute(
            "SELECT id, tts_text FROM phrases ORDER BY sort_order"
        ).fetchall()
    finally:
        conn.close()

    if not cells and not phrases:
        raise RuntimeError("No paradigms in the database. Run: python -m rdspan seed")

    grouped: dict[str, list[tuple[str, str]]] = {}
    for row in cells:
        grouped.setdefault(row["paradigm_id"], []).append((row["slot"], row["tts_text"]))

    cell_jobs: list[tuple[str, str, str, Path]] = []
    full_jobs: list[tuple[str, list[tuple[str, str]]]] = []
    phrase_jobs: list[tuple[str, str, Path]] = []
    skipped = 0

    for paradigm_id, items in grouped.items():
        full = cell_dir(paradigm_id) / "full.wav"
        if not force and audio_exists(full):
            skipped += 1
            _discard_cell_clips(paradigm_id)
            continue
        for slot, text in items:
            dest = cell_wav(paradigm_id, slot)
            if not force and audio_exists(dest):
                skipped += 1
            else:
                cell_jobs.append((paradigm_id, slot, text, dest))
        full_jobs.append((paradigm_id, items))

    for row in phrases:
        dest = phrase_wav(row["id"])
        if not force and audio_exists(dest):
            skipped += 1
        else:
            phrase_jobs.append((row["id"], row["tts_text"], dest))

    if not cell_jobs and not full_jobs and not phrase_jobs:
        return {"written": 0, "skipped": skipped}

    from piper import PiperVoice

    onnx = ensure_voice()
    voice = PiperVoice.load(str(onnx))
    length = config.piper_length_scale()
    written = 0

    for paradigm_id, slot, text, dest in cell_jobs:
        print(f"TTS {paradigm_id} {slot}: {text}", file=sys.stderr)
        _synthesize_wav(voice, text, dest, length)
        written += 1

    for paradigm_id, items in full_jobs:
        wavs = [p for p in (cell_wav(paradigm_id, s) for s, _ in items) if p.is_file()]
        if len(wavs) == len(items):
            full = cell_dir(paradigm_id) / "full.wav"
            _concat_wavs(wavs, full)
            _maybe_ogg(full)
            written += 1
        elif stitch_full_ogg(paradigm_id):
            written += 1
        _discard_cell_clips(paradigm_id)

    for phrase_id, text, dest in phrase_jobs:
        print(f"TTS phrase {phrase_id}: {text}", file=sys.stderr)
        _synthesize_wav(voice, text, dest, length)
        _maybe_ogg(dest)
        written += 1

    return {"written": written, "skipped": skipped}


def write_silence_wav(dest: Path, milliseconds: int = 300) -> None:
    """Tiny valid WAV for tests when Piper is unavailable."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    rate = 16000
    n = int(rate * milliseconds / 1000)
    with wave.open(str(dest), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
