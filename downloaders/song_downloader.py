#!/usr/bin/env python3
import argparse
import sys
import os
import time
import asyncio

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions and configs from the main script in same directory
from music_downloader import (
    download_from_deezer_bot,
    SongNotFoundOnDeezerError,
    add_failed_song,
    load_processed_songs,
    save_processed_songs,
)
from config import DOWNLOAD_DIR


def main():
    parser = argparse.ArgumentParser(description="Download a single song via Deezer bot.")
    parser.add_argument("--artist", required=True, help="The artist name.")
    parser.add_argument("--title", required=True, help="The song title.")
    args = parser.parse_args()

    artist = args.artist.strip()
    title = args.title.strip()
    song_key = f"{artist} - {title}"

    processed_songs = load_processed_songs()

    if song_key in processed_songs:
        print(f"Skipping '{song_key}' as it has already been downloaded.")
        sys.exit(0)

    try:
        file_path = asyncio.run(download_from_deezer_bot(artist, title))
        if file_path:
            print(f"✅ Successfully downloaded '{song_key}' from Deezer bot.")
            processed_songs[song_key] = {"timestamp": time.time(), "status": "processed"}
            save_processed_songs(processed_songs)
            sys.exit(0)
        else:
            raise SongNotFoundOnDeezerError(f"Download for '{song_key}' failed.")

    except SongNotFoundOnDeezerError as e:
        print(f"⚠️ Deezer bot failed: {e}")
        add_failed_song(artist, title, "N/A")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        add_failed_song(artist, title, "N/A")
        sys.exit(1)


if __name__ == "__main__":
    main()
