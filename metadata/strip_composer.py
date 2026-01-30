#!/usr/bin/env python3
import os
import sys
from mutagen import File

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MUSIC_DIR

def strip_composer_tags():
    for root, _, files in os.walk(MUSIC_DIR):
        for name in files:
            if name.lower().endswith((".flac", ".mp3", ".m4a", ".ogg")):
                path = os.path.join(root, name)
                try:
                    audio = File(path, easy=False)
                    if audio is None:
                        continue

                    if "composer" in audio:
                        print(f"Removing composer from: {path}")
                        del audio["composer"]
                        audio.save()

                except Exception as e:
                    print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    strip_composer_tags()
