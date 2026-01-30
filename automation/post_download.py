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

    # Support multiple audio formats - move files recursively from subdirectories
    extensions = (".mp3", ".flac", ".opus", ".m4a", ".ogg", ".wav", ".aiff", ".aac")

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(extensions):
                src = os.path.join(root, file)
                dst = os.path.join(MUSIC_DIR, file)

                shutil.move(src, dst)

                print(f"Moved: {file}")

    # Clean up empty subdirectories (session folders) and the source folder itself
    # Walk bottom-up to remove empty dirs from deepest first
    for root, dirs, files in os.walk(source_dir, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                os.rmdir(dir_path)
                print(f"Removed empty folder: {dir_path}")
            except OSError:
                pass  # Not empty or other error
    
    # Finally remove the source dir itself if it's a temp session folder
    if source_dir != DEFAULT_STAGING_DIR:
        try:
            os.rmdir(source_dir)
            print(f"Removed empty source folder: {source_dir}")
        except OSError:
            pass


if __name__ == "__main__":
    main()
