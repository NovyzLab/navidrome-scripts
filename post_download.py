import subprocess
import os
import shutil
import time

staging_dir = "/opt/navidrome/incoming"
music_dir = "/opt/navidrome/music"

time.sleep(1)

subprocess.run(['/usr/bin/python3', 'metadata_cleaner.py'])

subprocess.run(['/usr/bin/python3', 'lyrics_staging.py'])


extensions = (".mp3", ".flac")

for file in os.listdir(staging_dir):
    if file.lower().endswith(extensions):
        src = os.path.join(staging_dir, file)
        dst = os.path.join(music_dir, file)

        shutil.move(src, dst)

        print(f"Copied: {file}")
