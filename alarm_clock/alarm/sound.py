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
		self.audio_file = audio_file
		self.random_position = random_position or random.uniform

	def wake(self) -> None:
		import pygame
		from mutagen.mp3 import MP3

		pygame.mixer.init()
		total_length = MP3(self.audio_file).info.length
		start_time = self.random_position(0, max(0, total_length - 60))
		pygame.mixer.music.load(str(self.audio_file))
		pygame.mixer.music.play(loops=1, start=start_time, fade_ms=2000)

	def stop_alarm(self) -> None:
		import pygame

		if pygame.mixer.get_init():
			pygame.mixer.music.stop()
			pygame.mixer.quit()
