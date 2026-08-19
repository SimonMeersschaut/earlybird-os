"""Messages displayed by the alarm clock UI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """A message with an icon to display below the current time."""

    icon: str
    text: str