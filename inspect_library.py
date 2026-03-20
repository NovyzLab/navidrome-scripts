import os
from config import MUSIC_DIR
from mutagen import File

print(f"Library directory: {MUSIC_DIR}")

def inspect(name):
    print(f"\n--- Checking {name} ---")
    try:
        audio = File(name)
        if audio is None:
            print("Mutagen returned None")
            return
            
        keys = list(audio.keys())
        print(f"Keys: {keys}")
        
        if 'metadata_block_picture' in audio:
            pic_len = len(audio['metadata_block_picture'][0])
            print(f"✅ Found FLAC picture block: {pic_len} bytes")
        else:
            print("❌ No metadata_block_picture found by Mutagen!")
            
    except Exception as e:
        print(f"Error reading with Mutagen: {e}")

# First look for the specifically named file
named_file = os.path.join(MUSIC_DIR, "Beansclub - Ill Never Find This Sound Of Silence.opus")
if os.path.exists(named_file):
    inspect(named_file)
else:
    print(f"File not found exactly at: {named_file}")

# List all matching "Beansclub" regardless of case
print("\nScanning library for related files...")
for root, _, files in os.walk(MUSIC_DIR):
    for f in files:
        if "beansclub" in f.lower():
            inspect(os.path.join(root, f))
