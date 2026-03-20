import os
import sys
from config import MUSIC_DIR

print(f"Checking in {MUSIC_DIR}...")
for root, _, files in os.walk(MUSIC_DIR):
    for f in files:
        if "Beansclub" in f or "beansclub" in f:
            print(f"Found: {os.path.join(root, f)}")
            
            # Check with mutagenn
            try:
                from mutagen import File
                audio = File(os.path.join(root, f))
                if audio is not None:
                    print(f"Tags: {audio.keys()}")
                    if 'metadata_block_picture' in audio:
                        pic_data = audio['metadata_block_picture'][0]
                        print(f"HAS COVER ART: len={len(pic_data)}")
                    else:
                        print("NO COVER ART FOUND BY MUTAGEN")
            except Exception as e:
                print(f"Error: {e}")
            print("-" * 40)
