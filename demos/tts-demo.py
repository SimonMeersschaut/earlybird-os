import subprocess
import sys
from pathlib import Path


class PiperTTS:
    def __init__(self, piper_executable: str, model_path: str):
        self.piper = Path(piper_executable).resolve()
        self.model = Path(model_path).resolve()

        if not self.piper.is_file():
            raise FileNotFoundError(f"Piper binary not found at: {self.piper}")
        if not self.model.is_file():
            raise FileNotFoundError(f"Model file not found at: {self.model}")

    def speak(self, text: str, sample_rate: int = 22050):
        """Synthesize text and play it directly using aplay."""
        # 1. Start the Piper process (reading text from stdin, outputting raw audio to stdout)
        piper_cmd = [
            str(self.piper),
            "--model", str(self.model),
            "--output_raw"
        ]
        
        # 2. Start the aplay process (reading raw audio from stdin)
        aplay_cmd = [
            "aplay",
            "-r", str(sample_rate),
            "-f", "S16_LE",
            "-c", "1"
        ]

        piper_proc = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        aplay_proc = subprocess.Popen(
            aplay_cmd,
            stdin=piper_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Allow piper_proc to receive SIGPIPE if aplay exits
        piper_proc.stdout.close()

        # Send text to Piper
        piper_proc.stdin.write(text.encode("utf-8"))
        piper_proc.stdin.close()

        # Wait for audio to finish playing
        print("Playing audio")
        aplay_proc.wait()
        print("Done")


if __name__ == "__main__":
    # Adjust paths relative to where you installed Piper and downloaded the voice
    PIPER_PATH = "/home/earlybird/piper-tts/piper/piper"
    MODEL_PATH = "/home/earlybird/piper-tts/en_US-lessac-medium.onnx"

    tts = PiperTTS(piper_executable=PIPER_PATH, model_path=MODEL_PATH)

    print("Synthesizing speech...")
    tts.speak("Hello! This is running locally inside a Python script on your Raspberry Pi.")