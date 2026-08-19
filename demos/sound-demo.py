import random
import pygame
from mutagen.mp3 import MP3

def get_track_duration(audio_file):
    """Returns total duration of the audio file in seconds."""
    audio = MP3(audio_file)
    return audio.info.length

def start_alarm(audio_file="alarm.mp3"):
    """
    Starts playing the alarm sound from a random position in the track.
    """
    pygame.mixer.init()
    try:
        # Get duration and pick a random starting point
        total_length = get_track_duration(audio_file)
        start_time = random.uniform(0, max(0, total_length - 60))  # Leave at least 60s of audio
        
        # Load audio into music player
        pygame.mixer.music.load(audio_file)
        
        # play(loops, start_time_in_seconds)
        pygame.mixer.music.play(loops=-1, start=start_time)
        
        print(f"🔔 Alarm started at {start_time:.2f}s / {total_length:.2f}s!")
    except Exception as e:
        print(f"Error loading audio file: {e}")

def stop_alarm():
    """
    Stops sound playback and cleans up audio resources.
    """
    if pygame.mixer.get_init():
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        print("🔕 Alarm stopped.")

if __name__ == "__main__":
    start_alarm("alarm.mp3")
    
    print("Alarm playing in background... (Press Enter to stop)")
    input()
    
    stop_alarm()