import os
import re
import sys
import json
from typing import List, Dict, Optional

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen import File
except ImportError:
    print("Error: Mutagen library not found. Please install it with 'pip install mutagen' to run this script.")
    sys.exit(1)

# --- Configuration ---
DOWNLOAD_DIR = '/opt/navidrome/music/'

def strip_and_apply_metadata(file_path: str, artist: str, title: str):
    """
    Applies the correct artist and title metadata to a music file.
    """
    try:
        audio = File(file_path)
        if not audio:
            print(f"Skipping unsupported or invalid file: {file_path}")
            return
        
        tags_modified = False

        # --- Apply the correct artist and title from the filename ---
        if isinstance(audio, EasyID3):
            audio['artist'] = [artist]
            audio['title'] = [title]
        elif isinstance(audio, FLAC):
            audio['artist'] = [artist]
            audio['title'] = [title]
        elif isinstance(audio, MP4):
            audio['\xa9ART'] = [artist]
            audio['\xa9nam'] = [title]
        
        tags_modified = True
            
        if tags_modified:
            audio.save()
            print("Metadata updated successfully.")
        else:
            print("No metadata tags were modified.")
            
    except Exception as e:
        print(f"Error processing metadata for '{os.path.basename(file_path)}': {e}")

def main():
    """
    Finds all music files in the download directory and strips their metadata,
    using the filename to restore missing data.
    """
    print(f"Starting metadata cleanup for files in '{DOWNLOAD_DIR}'...")
    
    processed_count = 0
    
    # Iterate through the files on disk first
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.lower().endswith(('.mp3', '.flac', '.m4a')):
                file_path = os.path.join(root, file)
                print(f"\nProcessing: {file_path}")

                try:
                    filename_base = os.path.splitext(os.path.basename(file_path))[0]
                    artist = None
                    title = None

                    # Handle the "Artist - Title" format
                    parts_dash = filename_base.split(' - ', 1)
                    if len(parts_dash) == 2:
                        artist, title = parts_dash
                    else:
                        # Handle the "Artist_Title" format
                        parts_underscore = filename_base.split('_')
                        if len(parts_underscore) >= 2:
                            # Heuristically determine the artist from the first two words
                            # if the first two words are capitalized or look like a multi-word name.
                            first_two_words = ' '.join(parts_underscore[:2])
                            if (len(parts_underscore) > 2 and
                                (first_two_words[0].isupper() and first_two_words.split()[1][0].isupper())):
                                artist = first_two_words.replace('_', ' ')
                                title = ' '.join(parts_underscore[2:]).replace('_', ' ')
                            else:
                                artist = parts_underscore[0].replace('_', ' ')
                                title = ' '.join(parts_underscore[1:]).replace('_', ' ')

                    if artist and title:
                        print(f"Applying metadata from filename: '{artist} - {title}'")
                        strip_and_apply_metadata(file_path, artist, title)
                        processed_count += 1
                    else:
                        print(f"Skipping file with incorrect filename format: '{file}'")
                        
                except Exception as e:
                    print(f"An error occurred while processing file: {e}")
                    continue

    if processed_count == 0:
        print("No music files found to process.")
    else:
        print(f"\nCleanup complete. Processed {processed_count} files.")

if __name__ == "__main__":
    main()
