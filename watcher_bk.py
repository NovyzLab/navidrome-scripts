import time
import subprocess
import argparse
import sys
import os
import random
# --- Configuration ---
# The path to your main music downloader script
DOWNLOADER_SCRIPT = "/root/scripts/music_downloader.py"
# The interval (in seconds) to check for new songs
CHECK_INTERVAL_SECONDS = 15

def main():
    """Continuously monitors and runs the music downloader script."""
    
    parser = argparse.ArgumentParser(
        description='Continuously checks for new songs in playlists and runs the music downloader.'
    )
    parser.add_argument('--youtube-playlist-url', required=False, help='The YouTube playlist URL to monitor.')
    parser.add_argument('--listenbrainz-playlist-url', required=False, help='The ListenBrainz playlist URL to monitor.')
    
    args = parser.parse_args()
    
    # Check for required arguments
    if not args.youtube_playlist_url and not args.listenbrainz_playlist_url:
        print("Error: At least one of --youtube-playlist-url or --listenbrainz-playlist-url is required.")
        sys.exit(1) # Exit with an error code

    print(f"Starting playlist watcher, checking every {CHECK_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.")
    
    try:
        while True:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- [{timestamp}] Starting downloader cycle ---")
            
            # List to track which downloads ran successfully
            ran_successfully = []

            # --- 1. Run the music downloader for the YouTube playlist ---
            if args.youtube_playlist_url:
                try:
                    print(f"Running downloader for YouTube playlist: {args.youtube_playlist_url}")
                    # Executes the command: python3 music_downloader.py youtube --playlist-url <url>
                    subprocess.run(
                        ["python3", DOWNLOADER_SCRIPT, "youtube", "--playlist-url", args.youtube_playlist_url],
                        check=True, # Raise CalledProcessError if it fails
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    ran_successfully.append("YouTube")
                except subprocess.CalledProcessError as e:
                    print(f"YouTube Downloader Error (Code {e.returncode}): {e.stderr.strip()}")
                except FileNotFoundError:
                   print(f"Error: Python interpreter or downloader script '{DOWNLOADER_SCRIPT}' not found.")
            time.sleep(5)

            # --- 2. Run the music downloader for the ListenBrainz playlist ---
            if args.listenbrainz_playlist_url:
                try:
                    print(f"Running downloader for ListenBrainz playlist: {args.listenbrainz_playlist_url}")
                    # Executes the command: python3 music_downloader.py listenbrainz --playlist-url <url>
                    subprocess.run(
                        ["python3", DOWNLOADER_SCRIPT, "listenbrainz", "--playlist-url", args.listenbrainz_playlist_url],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    ran_successfully.append("ListenBrainz")
                except subprocess.CalledProcessError as e:
                    print(f"ListenBrainz Downloader Error (Code {e.returncode}): {e.stderr.strip()}")
                except FileNotFoundError:
                    # This error is critical and usually caught by the first block, but good to keep
                    pass 

            # Cycle summary
            if ran_successfully:
                print(f"[{timestamp}] Cycle complete. Downloaders run: {', '.join(ran_successfully)}.")
            else:
                print(f"[{timestamp}] Cycle complete. No downloaders ran or all failed.")


            # Wait for the specified interval before checking again
            print(f"Waiting {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS + random.uniform(-3, 3))
            
    except KeyboardInterrupt:
        print("\n\nWatcher script stopped by user. Goodbye!")
        # No lock cleanup needed!

if __name__ == "__main__":
    main()
