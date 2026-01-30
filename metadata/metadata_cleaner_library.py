import os
import re
import sys
from typing import List, Dict, Optional

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen import File
except ImportError:
    print("Error: Mutagen library not found. Please install it with 'pip install mutagen' to run this script.")
    sys.exit(1)

# --- Configuration from .env ---
from config import MUSIC_DIR as DOWNLOAD_DIR

def update_and_clean_metadata(file_path: str):
    """
    Combines artists from 'artist' and 'main_artist' tags, cleans them,
    and consolidates them into a single 'artist' tag. It also cleans other
    unwanted metadata tags.
    """
    try:
        audio = File(file_path)
        if not audio:
            print(f"Skipping unsupported or invalid file: {file_path}")
            return
        
        tags_modified = False
        all_artists = set()

        # --- Get artists from 'artist' tag ---
        artist_tag = audio.get('artist')
        if artist_tag and isinstance(artist_tag, list):
            for artist in artist_tag:
                cleaned_artist = re.sub(r'(\s+ft\.|\s+feat\.|\s*\/|\s*&|\s+and\s*|\s*,).+', '', artist, flags=re.IGNORECASE).strip()
                if cleaned_artist:
                    all_artists.add(cleaned_artist)
        
        # --- Get artists from 'main_artist' tag ---
        main_artist_tag = audio.get('main_artist')
        if main_artist_tag and isinstance(main_artist_tag, list):
            for artist in main_artist_tag:
                cleaned_artist = re.sub(r'(\s+ft\.|\s+feat\.|\s*\/|\s*&|\s+and\s*|\s*,).+', '', artist, flags=re.IGNORECASE).strip()
                if cleaned_artist:
                    all_artists.add(cleaned_artist)

        # --- Consolidate and update the 'artist' tag ---
        if all_artists:
            final_artist_string = ", ".join(sorted(list(all_artists)))
            if isinstance(audio, EasyID3) or isinstance(audio, FLAC):
                if audio.get('artist') != [final_artist_string]:
                    audio['artist'] = [final_artist_string]
                    tags_modified = True
            elif isinstance(audio, MP4):
                if audio.get('\xa9ART') != [final_artist_string]:
                    audio['\xa9ART'] = [final_artist_string]
                    tags_modified = True

        # --- Remove other conflicting or unwanted tags ---
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
            print("Metadata updated successfully.")
        else:
            print("No changes needed. Metadata is already clean.")
            
    except Exception as e:
        print(f"Error processing metadata for '{os.path.basename(file_path)}': {e}")

def main():
    """
    Finds all music files in the download directory and applies metadata,
    using the filename as the source of truth.
    """
    print(f"Starting metadata application for files in '{DOWNLOAD_DIR}'...")
    
    processed_count = 0
    
    # Iterate through the files on disk first
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.lower().endswith(('.mp3', '.flac', '.m4a')):
                file_path = os.path.join(root, file)
                print(f"\nProcessing: {file_path}")

                try:
                    update_and_clean_metadata(file_path)
                    processed_count += 1
                except Exception as e:
                    print(f"An error occurred while processing file: {e}")
                    continue

    if processed_count == 0:
        print("No music files found to process.")
    else:
        print(f"\nCleanup complete. Processed {processed_count} files.")

if __name__ == "__main__":
    main()
