#!/usr/bin/env python3
"""
Main orchestrator for the music download pipeline.
Fetches songs from configured sources and downloads using priority-based downloaders.
"""
import os
import sys
import json
import time
import asyncio
import argparse
import subprocess
import uuid
from datetime import datetime
from typing import List, Dict, Set

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import (
    INCOMING_DIR,
    YOUTUBE_PLAYLIST_URL,
    SOUNDCLOUD_PLAYLIST_URL,
    LISTENBRAINZ_PLAYLIST_URL,
    _data_dir
)
from sources.base import Song, SourceType
from sources.youtube import YouTubeSource
from sources.soundcloud import SoundCloudSource
from sources.listenbrainz import ListenBrainzSource
from downloaders.tidaloader import TidaloaderDownloader
from downloaders.deezer import DeezerDownloader
from downloaders.youtube import YouTubeDownloader
from downloaders.soundcloud import SoundCloudDownloader
from downloaders.base import SongNotFoundError


# Tracking file for processed songs
PROCESSED_FILE = str(_data_dir / 'processed_songs.json')


def load_processed_songs() -> Dict[str, Dict]:
    """Load the tracking file of processed songs."""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_processed_songs(data: Dict[str, Dict]):
    """Save the tracking file."""
    with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def fetch_all_songs() -> List[Song]:
    """
    Fetch songs from all configured sources.
    Returns a deduplicated list of songs.
    """
    all_songs: List[Song] = []
    
    # YouTube source
    if YOUTUBE_PLAYLIST_URL:
        source = YouTubeSource()
        songs = source.get_songs(YOUTUBE_PLAYLIST_URL)
        all_songs.extend(songs)
        print(f"  → {len(songs)} songs from YouTube")
    
    # SoundCloud source
    if SOUNDCLOUD_PLAYLIST_URL:
        source = SoundCloudSource()
        songs = source.get_songs(SOUNDCLOUD_PLAYLIST_URL)
        all_songs.extend(songs)
        print(f"  → {len(songs)} songs from SoundCloud")
    
    # ListenBrainz source
    if LISTENBRAINZ_PLAYLIST_URL:
        source = ListenBrainzSource()
        songs = source.get_songs(LISTENBRAINZ_PLAYLIST_URL)
        all_songs.extend(songs)
        print(f"  → {len(songs)} songs from ListenBrainz")
    
    # Deduplicate by artist-title key
    seen: Set[str] = set()
    unique_songs: List[Song] = []
    for song in all_songs:
        key = song.key.lower()
        if key not in seen:
            seen.add(key)
            unique_songs.append(song)
    
    print(f"\nTotal: {len(unique_songs)} unique songs (after deduplication)")
    return unique_songs


async def download_song(song: Song, download_dir: str, downloaders: list) -> tuple[bool, bool, str | None]:
    """
    Try to download a song using available downloaders in priority order.
    
    Args:
        song: The Song to download.
        download_dir: Directory to save files.
        downloaders: List of downloader instances, sorted by priority.
        
    Returns:
        Tuple of (success, skip_post_processing, downloader_name)
    """
    for downloader in downloaders:
        if not downloader.is_available():
            continue
        
        # For source-specific downloaders, check if they can handle this song
        if not downloader.can_handle(song):
            continue
        
        try:
            result = await downloader.download(song, download_dir)
            if result:
                print(f"✓ Downloaded via {downloader.name}: {song.artist} - {song.title}")
                skip_post = getattr(downloader, 'skip_post_processing', False)
                return True, skip_post, downloader.name
        except SongNotFoundError as e:
            print(f"✗ {downloader.name}: {e}")
            continue
        except Exception as e:
            print(f"✗ {downloader.name} error: {e}")
            continue
    
    print(f"✗ Failed to download: {song.artist} - {song.title}")
    return False, False, None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download music from configured playlist sources.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources are configured in .env:
  YOUTUBE_PLAYLIST_URL       YouTube playlist
  SOUNDCLOUD_PLAYLIST_URL    SoundCloud playlist/user
  LISTENBRAINZ_PLAYLIST_URL  ListenBrainz playlist

Download priority: Deezer (FLAC) → Source-native (YouTube/SoundCloud)
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch songs but do not download')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Music Download Pipeline")
    print("=" * 60)
    
    # Fetch songs from all sources
    print("\n📋 Fetching songs from sources...")
    songs = fetch_all_songs()
    
    if not songs:
        print("No songs found from any source. Exiting.")
        sys.exit(0)
    
    # Filter out already processed songs
    processed = load_processed_songs()
    new_songs = [s for s in songs if s.key not in processed]
    
    print(f"\n🎵 {len(new_songs)} new songs to download ({len(songs) - len(new_songs)} already processed)")
    
    if not new_songs:
        print("Nothing new to download. Exiting.")
        sys.exit(0)
    
    if args.dry_run:
        print("\n[DRY RUN] Would download:")
        for song in new_songs:
            print(f"  - {song.artist} - {song.title} [{song.source.value}]")
        sys.exit(0)
    
    # Initialize downloaders (sorted by priority)
    downloaders = sorted([
        TidaloaderDownloader(),  # Priority 5 - FLAC, direct to library
        DeezerDownloader(),      # Priority 10 - FLAC via Telegram
        YouTubeDownloader(),     # Priority 50 - fallback
        SoundCloudDownloader(),  # Priority 50 - fallback
    ], key=lambda d: d.priority)
    
    # Show available downloaders
    print("\n🔧 Available downloaders:")
    for d in downloaders:
        status = "✓" if d.is_available() else "✗"
        print(f"  {status} {d.name} (priority: {d.priority})")
    
    # Create session folder
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    temp_dir = os.path.join(INCOMING_DIR, f"session_{session_id}")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"\n📁 Download folder: {temp_dir}")
    
    # Download songs
    print("\n" + "=" * 60)
    print("Starting downloads...")
    print("=" * 60 + "\n")
    
    songs_downloaded = False
    needs_post_processing = False
    
    for i, song in enumerate(new_songs, 1):
        print(f"[{i}/{len(new_songs)}] {song.artist} - {song.title}")
        
        success, skip_post, downloaded_from = asyncio.run(download_song(song, temp_dir, downloaders))
        
        if success:
            songs_downloaded = True
            if not skip_post:
                needs_post_processing = True
        
        # Mark as processed
        song_entry = {
            'timestamp': time.time(),
            'source': song.source.value,
            'status': 'downloaded' if success else 'failed'
        }
        
        if success and downloaded_from:
            song_entry['downloaded_from'] = downloaded_from
            
        processed[song.key] = song_entry
        save_processed_songs(processed)
        
        print("-" * 40)
        time.sleep(1)  # Be nice to servers
    
    # Run post-processing only if needed
    if needs_post_processing:
        print(f"\n🔄 Running post-download processing...")
        post_script = os.path.join(PROJECT_ROOT, 'automation', 'post_download.py')
        subprocess.run([sys.executable, post_script, '--source-dir', temp_dir])
    elif songs_downloaded:
        print("\n✓ All songs downloaded via Tidaloader (no post-processing needed)")
    else:
        print("\nNo songs downloaded.")
    
    # Cleanup empty temp dir
    try:
        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except OSError:
        pass
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
