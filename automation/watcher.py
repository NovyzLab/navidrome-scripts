import time
import subprocess
import argparse
import sys
import os
import random

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Configuration from .env ---
from config import (
    MAIN_DOWNLOADER_SCRIPT,
    YT_DOWNLOADER_SCRIPT,
    SC_DOWNLOADER_SCRIPT,
    CHECK_INTERVAL_SECONDS,
    YOUTUBE_PLAYLIST_URL,
    LISTENBRAINZ_PLAYLIST_URL,
    YT2_PLAYLIST_URL,
    SOUNDCLOUD_PLAYLIST_URL,
)

def run_downloader(name, command):
    """Helper function to execute a downloader command with consistent logging."""
    try:
        print(f"Running downloader for {name}...")
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"{name} Downloader Error (Code {e.returncode}): {e.stderr.strip()}")
    except FileNotFoundError:
        print(f"Error: Downloader script not found for {name}: {command[1]}")
    return False


def main():
    """Continuously monitors and runs the downloader scripts."""
    parser = argparse.ArgumentParser(
        description='Continuously checks for new songs in playlists and runs the music downloaders.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Playlist URLs can be configured in .env or passed as arguments (arguments override .env).

Examples:
  # Use playlist URLs from .env
  python watcher.py
  
  # Override specific playlists via command line
  python watcher.py --youtube-playlist-url "https://youtube.com/playlist?list=..."
  
  # Use only SoundCloud
  python watcher.py --soundcloud-url "https://soundcloud.com/artist/sets/playlist"
        """
    )
    parser.add_argument('--youtube-playlist-url', required=False,
                        help='The YouTube playlist URL to monitor for the main downloader (overrides .env).')
    parser.add_argument('--listenbrainz-playlist-url', required=False,
                        help='The ListenBrainz playlist URL to monitor (overrides .env).')
    parser.add_argument('--yt2-playlist-url', required=False,
                        help='The YouTube playlist URL for yt_downloader2.py (overrides .env).')
    parser.add_argument('--soundcloud-url', required=False,
                        help='The SoundCloud playlist/user URL to monitor (overrides .env).')

    args = parser.parse_args()

    # Use command-line args if provided, otherwise fall back to .env values
    youtube_url = args.youtube_playlist_url or YOUTUBE_PLAYLIST_URL
    listenbrainz_url = args.listenbrainz_playlist_url or LISTENBRAINZ_PLAYLIST_URL
    yt2_url = args.yt2_playlist_url or YT2_PLAYLIST_URL
    soundcloud_url = args.soundcloud_url or SOUNDCLOUD_PLAYLIST_URL

    # Check if at least one URL is configured
    if not any([youtube_url, listenbrainz_url, yt2_url, soundcloud_url]):
        print("Error: No playlist URLs configured.")
        print("Either set them in .env or provide them as command-line arguments.")
        print("Run with --help for more information.")
        sys.exit(1)

    # Show which sources are enabled
    print("Configured sources:")
    if youtube_url:
        print(f"  - YouTube (main/Deezer): {youtube_url[:50]}...")
    if listenbrainz_url:
        print(f"  - ListenBrainz: {listenbrainz_url[:50]}...")
    if yt2_url:
        print(f"  - YouTube (secondary): {yt2_url[:50]}...")
    if soundcloud_url:
        print(f"  - SoundCloud: {soundcloud_url[:50]}...")

    print(f"\nStarting playlist watcher, checking every {CHECK_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    try:
        while True:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- [{timestamp}] Starting downloader cycle ---")

            ran_successfully = []

            # --- 1. YouTube Downloader (main - uses Deezer bot) ---
            if youtube_url:
                ok = run_downloader(
                    "YouTube (main)",
                    ["python3", MAIN_DOWNLOADER_SCRIPT, "youtube", "--playlist-url", youtube_url]
                )
                if ok:
                    ran_successfully.append("YouTube (main)")
                time.sleep(5)

            # --- 2. ListenBrainz Downloader ---
            if listenbrainz_url:
                ok = run_downloader(
                    "ListenBrainz",
                    ["python3", MAIN_DOWNLOADER_SCRIPT, "listenbrainz", "--playlist-url", listenbrainz_url]
                )
                if ok:
                    ran_successfully.append("ListenBrainz")
                time.sleep(5)

            # --- 3. Second YouTube Downloader (yt_downloader2.py - direct download) ---
            if yt2_url:
                ok = run_downloader(
                    "YouTube (secondary)",
                    ["python3", YT_DOWNLOADER_SCRIPT, "--playlist-url", yt2_url]
                )
                if ok:
                    ran_successfully.append("YouTube (secondary)")
                time.sleep(5)

            # --- 4. SoundCloud Downloader ---
            if soundcloud_url:
                ok = run_downloader(
                    "SoundCloud",
                    ["python3", SC_DOWNLOADER_SCRIPT, "-l", soundcloud_url]
                )
                if ok:
                    ran_successfully.append("SoundCloud")
                time.sleep(5)

            # --- Summary ---
            if ran_successfully:
                print(f"[{timestamp}]  Cycle complete. Downloaders run: {', '.join(ran_successfully)}.")
            else:
                print(f"[{timestamp}]  Cycle complete. No downloaders ran or all failed.")

            # --- Wait before next cycle ---
            print(f"Waiting {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS + random.uniform(-3, 3))

    except KeyboardInterrupt:
        print("\n\nWatcher script stopped by user. Goodbye!")


if __name__ == "__main__":
    main()
