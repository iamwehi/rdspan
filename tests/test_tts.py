import wave

from rdspan.tts import CELL_SLOTS, _concat_wavs, _discard_cell_clips, cell_dir, write_silence_wav


def test_concat_inserts_pause_between_clips_not_after_last(tmp_path):
    a = tmp_path / "a.wav"
    b = tmp_path / "b.wav"
    write_silence_wav(a, 100)
    write_silence_wav(b, 100)
    out = tmp_path / "full.wav"
    _concat_wavs([a, b], out, pause_ms=200)
    with wave.open(str(out), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        # 100ms + 200ms pause + 100ms, no trailing pause
        assert wav_file.getnframes() == int(16000 * 0.4)


def test_discard_cell_clips_keeps_full_track(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIO_PATH", str(tmp_path))
    directory = cell_dir("hablar.presente.indicativo")
    directory.mkdir(parents=True)
    (directory / "full.ogg").write_bytes(b"full")
    for slot in CELL_SLOTS:
        (directory / f"{slot}.ogg").write_bytes(b"cell")
        (directory / f"{slot}.wav").write_bytes(b"cell")
    _discard_cell_clips("hablar.presente.indicativo")
    assert (directory / "full.ogg").is_file()
    for slot in CELL_SLOTS:
        assert not (directory / f"{slot}.ogg").exists()
        assert not (directory / f"{slot}.wav").exists()
