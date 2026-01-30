import subprocess
import os
import sys
import shutil
import time
import argparse

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import paths from config
from config import INCOMING_DIR, MUSIC_DIR

# Get the project root directory for finding other scripts
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default staging directory from config
DEFAULT_STAGING_DIR = INCOMING_DIR


def main():
    parser = argparse.ArgumentParser(description='Post-download processing for music files.')
    parser.add_argument('--source-dir', default=DEFAULT_STAGING_DIR,
                        help=f'Source directory containing downloaded music files (default: {DEFAULT_STAGING_DIR})')
    args = parser.parse_args()

    source_dir = args.source_dir
    print(f"Processing files in: {source_dir}")

    time.sleep(1)

    # Pass the source directory to the sub-scripts (using absolute paths)
    metadata_cleaner = os.path.join(PROJECT_ROOT, 'metadata', 'metadata_cleaner.py')
    lyrics_staging = os.path.join(PROJECT_ROOT, 'lyrics', 'lyrics_staging.py')
    
    subprocess.run(['/usr/bin/python3', metadata_cleaner, '--source-dir', source_dir])

    subprocess.run(['/usr/bin/python3', lyrics_staging, '--source-dir', source_dir])

    # Support multiple audio formats
    extensions = (".mp3", ".flac", ".opus", ".m4a", ".ogg", ".wav", ".aiff", ".aac")

    for file in os.listdir(source_dir):
        if file.lower().endswith(extensions):
            src = os.path.join(source_dir, file)
            dst = os.path.join(MUSIC_DIR, file)

            shutil.move(src, dst)

            print(f"Moved: {file}")

    # Clean up the temporary folder if it's empty
    if source_dir != DEFAULT_STAGING_DIR:
        try:
            os.rmdir(source_dir)
            print(f"Removed empty temporary folder: {source_dir}")
        except OSError:
            # Folder not empty or other error - that's fine
            pass


if __name__ == "__main__":
    main()
