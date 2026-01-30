# Navidrome Scripts

A collection of Python scripts for automating music downloads, metadata management, and lyrics fetching for Navidrome.

## 📁 Folder Structure

```
navidrome-scripts/
├── downloaders/              # Music downloading scripts
│   ├── music_downloader.py   # Main downloader (Deezer bot via Telegram)
│   ├── song_downloader.py    # Single song downloader
│   ├── yt_downloader2.py     # YouTube direct downloader
│   └── sc_downloader.py      # SoundCloud downloader
│
├── metadata/                 # Metadata processing scripts
│   ├── metadata_cleaner.py   # Clean metadata from incoming files
│   ├── metadata_cleaner_library.py  # Clean metadata in library
│   ├── metadata_recover.py   # Recover metadata from filenames
│   ├── print_metadata.py     # Print metadata for a file
│   └── strip_composer.py     # Remove composer tags
│
├── lyrics/                   # Lyrics fetching scripts
│   ├── get_lyrics.py         # Fetch lyrics for library
│   └── lyrics_staging.py     # Fetch lyrics for incoming files
│
├── automation/               # Automation & orchestration
│   ├── watcher.py            # Continuous playlist watcher
│   └── post_download.py      # Post-download processing pipeline
│
├── data/                     # State/tracking files (gitignored)
│   ├── failed_songs.json     # Songs that failed to download
│   ├── processed_songs.json  # Successfully processed songs
│   ├── yt_downloaded.json    # YouTube download history
│   ├── sc_downloaded.json    # SoundCloud download history
│   └── *.session             # Telegram session files
│
├── config.py                 # Centralized configuration loader
├── .env                      # Your configuration (gitignored)
├── .env.example              # Configuration template
├── requirements.txt          # Python dependencies
└── .gitignore
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# On Arch Linux
sudo pacman -S python-dotenv python-yt-dlp python-mutagen python-requests
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run Scripts

```bash
# Download from a YouTube playlist (via Deezer bot)
python downloaders/music_downloader.py youtube --playlist-url "YOUR_PLAYLIST_URL"

# Download from ListenBrainz playlist
python downloaders/music_downloader.py listenbrainz --playlist-url "YOUR_PLAYLIST_URL"

# Download from SoundCloud
python downloaders/sc_downloader.py -l "SOUNDCLOUD_URL"

# Run the watcher (continuous monitoring)
python automation/watcher.py
```

## ⚙️ Configuration

All configuration is managed via the `.env` file:

| Variable | Description |
|----------|-------------|
| `INCOMING_DIR` | Staging folder for new downloads |
| `MUSIC_DIR` | Main music library folder |
| `LYRICS_DIR` | Folder to store lyrics files |
| `TG_API_ID` | Telegram API ID (from my.telegram.org) |
| `TG_API_HASH` | Telegram API Hash |
| `TG_SESSION_NAME` | Telegram session name |
| `CHECK_INTERVAL_SECONDS` | How often watcher checks (default: 15) |

## 📄 License

MIT License
