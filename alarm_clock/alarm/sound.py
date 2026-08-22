"""Sound wakeup implementation."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable


class PygameAudioAlarm:
	"""Play the alarm track from a random position and loop it."""

	def __init__(
		self,
		audio_file: Path,
		random_position: Callable[[float, float], float] | None = None,
	) -> None:
		self.audio_file = Path(audio_file)
		self.random_position = random_position or random.uniform

	def wake(self) -> None:
		if not self.audio_file.exists():
			raise FileNotFoundError(f"Alarm audio file not found: {self.audio_file}")

		import pygame
		from mutagen.mp3 import MP3

		if not pygame.mixer.get_init():
			pygame.mixer.init()

		total_length = MP3(self.audio_file).info.length
		start_time = self.random_position(0, max(0, total_length - 60))
		pygame.mixer.music.load(str(self.audio_file))
		try:
			pygame.mixer.music.play(loops=-1, start=start_time, fade_ms=2000)
		except (pygame.error, NotImplementedError, TypeError, ValueError):
			# Some pygame/mp3 backends cannot seek on start; retry from the beginning.
			pygame.mixer.music.play(loops=-1, fade_ms=2000)

	def stop_alarm(self) -> None:
		import pygame

		if pygame.mixer.get_init():
			pygame.mixer.music.stop()
			pygame.mixer.quit()
