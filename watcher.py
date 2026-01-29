import time
import subprocess
import argparse
import sys
import os
import random

# --- Configuration ---
# Paths to your downloader scripts
MAIN_DOWNLOADER_SCRIPT = "/root/scripts/music_downloader.py"
YT_DOWNLOADER_SCRIPT = "/root/scripts/yt_downloader2.py"

# The interval (in seconds) to check for new songs
CHECK_INTERVAL_SECONDS = 15

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
        description='Continuously checks for new songs in playlists and runs the music downloaders.'
    )
    parser.add_argument('--youtube-playlist-url', required=False,
                        help='The YouTube playlist URL to monitor for the main downloader.')
    parser.add_argument('--listenbrainz-playlist-url', required=False,
                        help='The ListenBrainz playlist URL to monitor.')
    parser.add_argument('--yt2-playlist-url', required=False,
                        help='The second dedicated YouTube playlist URL for yt_downloader2.py.')

    args = parser.parse_args()

    if not any([args.youtube_playlist_url, args.listenbrainz_playlist_url, args.yt2_playlist_url]):
        print("Error: At least one playlist URL must be provided.")
        sys.exit(1)

    print(f"Starting playlist watcher, checking every {CHECK_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")

    try:
        while True:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- [{timestamp}] Starting downloader cycle ---")

            ran_successfully = []

            # --- 1. YouTube Downloader (main) ---
            if args.youtube_playlist_url:
                ok = run_downloader(
                    "YouTube (main)",
                    ["python3", MAIN_DOWNLOADER_SCRIPT, "youtube", "--playlist-url", args.youtube_playlist_url]
                )
                if ok:
                    ran_successfully.append("YouTube (main)")
                time.sleep(5)

            # --- 2. ListenBrainz Downloader ---
            if args.listenbrainz_playlist_url:
                ok = run_downloader(
                    "ListenBrainz",
                    ["python3", MAIN_DOWNLOADER_SCRIPT, "listenbrainz", "--playlist-url", args.listenbrainz_playlist_url]
                )
                if ok:
                    ran_successfully.append("ListenBrainz")
                time.sleep(5)

            # --- 3. Second YouTube Downloader (yt_downloader2.py) ---
            if args.yt2_playlist_url:
                ok = run_downloader(
                    "YouTube (secondary)",
                    ["python3", YT_DOWNLOADER_SCRIPT, "--playlist-url", args.yt2_playlist_url]
                )
                if ok:
                    ran_successfully.append("YouTube (secondary)")
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
