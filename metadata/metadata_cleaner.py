import os
import re
import sys
import shutil
import argparse
from typing import List, Dict, Optional

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen import File
except ImportError:
    print("Error: Mutagen library not found. Please install it with 'pip install mutagen'")
    sys.exit(1)

# --- Configuration from .env ---
from config import INCOMING_DIR, LIBRARY_DIR

def update_and_clean_metadata(file_path: str):
    """
    Cleans and consolidates metadata tags in audio files.
    """
    try:
        audio = File(file_path)
        if not audio:
            print(f"Skipping unsupported or invalid file: {file_path}")
            return False
        
        tags_modified = False
        all_artists = set()

        # --- Extract artists from tags ---
        for tag_name in ('artist', 'main_artist'):
            tag = audio.get(tag_name)
            if tag and isinstance(tag, list):
                for artist in tag:
                    # Include both regular comma and Unicode fullwidth comma (，)
                    cleaned_artist = re.sub(
                        r'(\s+ft\.|\s+feat\.|\s*\/|\s*&|\s+and\s*|\s*,|\s*，).+',
                        '', artist, flags=re.IGNORECASE
                    ).strip()
                    if cleaned_artist:
                        all_artists.add(cleaned_artist)

        # --- Consolidate and update artist field ---
        if all_artists:
            final_artist = ", ".join(sorted(all_artists))
            current_artist = audio.get('artist')
            
            # Check if update is needed
            if current_artist != [final_artist]:
                audio['artist'] = [final_artist]
                tags_modified = True

        # --- Remove unwanted tags ---
        unwanted_tags = [
            'main_artist', 'composer', 'performer', 'musicbrainz_trackid',
            'musicbrainz_albumid', 'author', 'itunesadvisory', 'PUBLISHER',
            'beat maker', 'COPYRIGHT', 'ARTISTS'
        ]
        for tag in unwanted_tags:
            if tag in audio:
                del audio[tag]
                tags_modified = True
            elif tag.lower() in audio:
                del audio[tag.lower()]
                tags_modified = True

        if tags_modified:
            audio.save()
            print(f"Metadata cleaned for: {os.path.basename(file_path)}")
        else:
            print(f"o changes needed for: {os.path.basename(file_path)}")

        return True
            
    except Exception as e:
        print(f"Error processing '{os.path.basename(file_path)}': {e}")
        return False

def move_to_library(file_path: str):
    """
    Moves a cleaned file from INCOMING_DIR to LIBRARY_DIR.
    """
    try:
        filename = os.path.basename(file_path)
        dest_path = os.path.join(LIBRARY_DIR, filename)

        if os.path.exists(dest_path):
            print(f"ile already exists in library, skipping: {filename}")
            os.remove(file_path)
            return

        shutil.move(file_path, dest_path)
        print(f"Moved '{filename}' → Library.")
    except Exception as e:
        print(f"Error moving '{file_path}' to library: {e}")

def main():
    """
    Processes all new files in the incoming folder , cleans metadata,
    and /moves them to the main library/ ==> runs lyrics finder instead.
    """
    parser = argparse.ArgumentParser(description='Clean metadata from audio files.')
    parser.add_argument('--source-dir', default=INCOMING_DIR,
                        help=f'Source directory containing audio files (default: {INCOMING_DIR})')
    args = parser.parse_args()

    source_dir = args.source_dir
    print(f"Starting metadata cleaner for '{source_dir}'...")
    processed = 0

    for root, _, files in os.walk(source_dir):
        for file in files:
            # Support multiple audio formats
            if not file.lower().endswith(('.mp3', '.flac', '.m4a', '.opus', '.ogg', '.wav', '.aiff', '.aac')):
                continue

            file_path = os.path.join(root, file)
            print(f"\nProcessing: {file}")

            if update_and_clean_metadata(file_path):
                processed += 1

    if processed == 0:
        print("No new songs found in incoming folder.")
    else:
        print(f"\nCleanup complete. {processed} files processed.")

if __name__ == "__main__":
    main()
