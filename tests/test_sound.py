from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.modules.setdefault("phue", SimpleNamespace(Bridge=object))

from alarm_clock.alarm.sound import PygameAudioAlarm


class _FakeMusic:
    def __init__(self, fail_with_start: bool = False) -> None:
        self.fail_with_start = fail_with_start
        self.loads: list[str] = []
        self.play_calls: list[dict[str, float | int]] = []

    def load(self, path: str) -> None:
        self.loads.append(path)

    def play(self, **kwargs) -> None:
        self.play_calls.append(kwargs)
        if self.fail_with_start and "start" in kwargs:
            raise RuntimeError("start position unsupported")


class _FakeMixer:
    def __init__(self, music: _FakeMusic) -> None:
        self.music = music
        self._inited = False
        self.init_calls = 0

    def init(self) -> None:
        self._inited = True
        self.init_calls += 1

    def get_init(self):
        return self._inited


class _FakeMP3:
    def __init__(self, _path: Path) -> None:
        self.info = SimpleNamespace(length=180.0)


def test_wake_loads_alarm_file_and_loops(monkeypatch, tmp_path: Path) -> None:
    alarm_file = tmp_path / "alarm.mp3"
    alarm_file.write_bytes(b"test")

    music = _FakeMusic()
    mixer = _FakeMixer(music)
    fake_pygame = SimpleNamespace(mixer=mixer, error=RuntimeError)

    monkeypatch.setitem(sys.modules, "pygame", fake_pygame)
    monkeypatch.setitem(sys.modules, "mutagen", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mutagen.mp3", SimpleNamespace(MP3=_FakeMP3))

    alarm = PygameAudioAlarm(alarm_file, random_position=lambda _a, _b: 12.5)
    alarm.wake()

    assert mixer.init_calls == 1
    assert music.loads == [str(alarm_file)]
    assert music.play_calls == [{"loops": -1, "start": 12.5, "fade_ms": 2000}]


def test_wake_retries_without_start_when_backend_does_not_support_seek(
    monkeypatch, tmp_path: Path
) -> None:
    alarm_file = tmp_path / "alarm.mp3"
    alarm_file.write_bytes(b"test")

    music = _FakeMusic(fail_with_start=True)
    mixer = _FakeMixer(music)
    fake_pygame = SimpleNamespace(mixer=mixer, error=RuntimeError)

    monkeypatch.setitem(sys.modules, "pygame", fake_pygame)
    monkeypatch.setitem(sys.modules, "mutagen", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "mutagen.mp3", SimpleNamespace(MP3=_FakeMP3))

    alarm = PygameAudioAlarm(alarm_file, random_position=lambda _a, _b: 24.0)
    alarm.wake()

    assert len(music.play_calls) == 2
    assert music.play_calls[0] == {"loops": -1, "start": 24.0, "fade_ms": 2000}
    assert music.play_calls[1] == {"loops": -1, "fade_ms": 2000}


def test_wake_raises_when_audio_file_is_missing(tmp_path: Path) -> None:
    missing = tmp_path / "alarm.mp3"

    alarm = PygameAudioAlarm(missing)

    try:
        alarm.wake()
    except FileNotFoundError as error:
        assert str(missing) in str(error)
    else:
        raise AssertionError("Expected FileNotFoundError")
