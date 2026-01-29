import subprocess
import os
import shutil
import time
import argparse

# Import paths from config
from config import INCOMING_DIR, MUSIC_DIR

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

    # Pass the source directory to the sub-scripts
    subprocess.run(['/usr/bin/python3', 'metadata_cleaner.py', '--source-dir', source_dir])

    subprocess.run(['/usr/bin/python3', 'lyrics_staging.py', '--source-dir', source_dir])

    extensions = (".mp3", ".flac")

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
