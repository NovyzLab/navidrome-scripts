"""
Centralized configuration module for Navidrome scripts.
Loads settings from .env file using python-dotenv.
"""
import os
import sys
from pathlib import Path

# Try to load dotenv, provide helpful error if not installed
try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is required. Please install it with: pip install python-dotenv")
    sys.exit(1)

# Load .env from the same directory as this config file
_env_path = Path(__file__).parent / '.env'
if not _env_path.exists():
    print(f"Warning: .env file not found at {_env_path}")
    print("Please copy .env.example to .env and configure your settings.")
    
load_dotenv(_env_path)

# ===================
# Directory Paths
# ===================
INCOMING_DIR = os.getenv('INCOMING_DIR', '/opt/navidrome/incoming/')
MUSIC_DIR = os.getenv('MUSIC_DIR', '/opt/navidrome/music/')
LYRICS_DIR = os.getenv('LYRICS_DIR', '/opt/navidrome/lyrics/')

# Aliases for backward compatibility
DOWNLOAD_DIR = INCOMING_DIR
LIBRARY_DIR = MUSIC_DIR

# ===================
# Telegram Configuration
# ===================
TG_API_ID = os.getenv('TG_API_ID', '')
TG_API_HASH = os.getenv('TG_API_HASH', '')
TG_SESSION_NAME = os.getenv('TG_SESSION_NAME', 'deezer_music_downloader')
DEEZER_BOT_USERNAME = os.getenv('DEEZER_BOT_USERNAME', '@deezload2bot')

# ===================
# Watcher Configuration
# ===================
MAIN_DOWNLOADER_SCRIPT = os.getenv('MAIN_DOWNLOADER_SCRIPT', '/root/scripts/music_downloader.py')
YT_DOWNLOADER_SCRIPT = os.getenv('YT_DOWNLOADER_SCRIPT', '/root/scripts/yt_downloader2.py')
SC_DOWNLOADER_SCRIPT = os.getenv('SC_DOWNLOADER_SCRIPT', '/root/scripts/sc_downloader.py')
CHECK_INTERVAL_SECONDS = int(os.getenv('CHECK_INTERVAL_SECONDS', '15'))

# ===================
# Playlist URLs (for watcher.py)
# ===================
YOUTUBE_PLAYLIST_URL = os.getenv('YOUTUBE_PLAYLIST_URL', '')
LISTENBRAINZ_PLAYLIST_URL = os.getenv('LISTENBRAINZ_PLAYLIST_URL', '')
YT2_PLAYLIST_URL = os.getenv('YT2_PLAYLIST_URL', '')
SOUNDCLOUD_PLAYLIST_URL = os.getenv('SOUNDCLOUD_PLAYLIST_URL', '')

# ===================
# Miscellaneous
# ===================
USER_AGENT = os.getenv('USER_AGENT', 'MusicDownloadScript/1.0')

# ===================
# File paths for tracking state (stored in data/ subdirectory)
# ===================
_script_dir = Path(__file__).parent
_data_dir = _script_dir / 'data'
FAILED_SONGS_FILE = str(_data_dir / 'failed_songs.json')
PROCESSED_SONGS_FILE = str(_data_dir / 'processed_songs.json')
DOWNLOADED_FILE = str(_data_dir / 'yt_downloaded.json')
TG_SESSION_PATH = str(_data_dir / TG_SESSION_NAME)


def validate_telegram_config():
    """Check that Telegram credentials are set and return True if valid."""
    if not TG_API_ID or not TG_API_HASH:
        print("Error: Missing TG_API_ID or TG_API_HASH in .env file.")
        print("Please update your .env file with valid Telegram API credentials.")
        return False
    return True
