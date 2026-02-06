# Navidrome Scripts

A collection of Python scripts for automating music downloads, metadata management, and lyrics fetching for Navidrome.

## 📁 Folder Structure

```
navidrome-scripts/
├── main.py                   # Main orchestrator (run this!)
│
├── sources/                  # Playlist/source fetchers
│   ├── base.py               # Song dataclass & abstract base
│   ├── youtube.py            # YouTube playlist fetcher
│   ├── soundcloud.py         # SoundCloud playlist/user fetcher
│   └── listenbrainz.py       # ListenBrainz playlist fetcher
│
├── downloaders/              # Download implementations
│   ├── base.py               # Abstract downloader base
│   ├── deezer.py             # Deezer bot (Telegram) - FLAC
│   ├── youtube.py            # YouTube direct (yt-dlp)
│   └── soundcloud.py         # SoundCloud direct (yt-dlp)
│
├── metadata/                 # Metadata processing
│   ├── metadata_cleaner.py   # Clean incoming file metadata
│   ├── metadata_cleaner_library.py  # Clean library metadata
│   └── print_metadata.py     # Debug: print file metadata
│
├── lyrics/                   # Lyrics fetching
│   ├── get_lyrics.py         # Fetch lyrics for library
│   └── lyrics_staging.py     # Fetch lyrics for incoming
│
├── automation/               # Automation
│   ├── watcher.py            # Continuous monitoring
│   └── post_download.py      # Post-download pipeline
│
├── data/                     # State files (gitignored)
│   ├── processed_songs.json  # Download history
│   └── *.session             # Telegram sessions
│
├── config.py                 # Configuration loader
├── .env                      # Your config (gitignored)
└── .env.example              # Config template
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your playlist URLs and Telegram credentials
```

### 3. Run

```bash
# Run once (download from all configured sources)
python main.py

# Dry run (show what would be downloaded)
python main.py --dry-run

# Continuous monitoring
python automation/watcher.py
```

## 🔄 How It Works

1. **Fetch** - `main.py` fetches songs from all configured sources (YouTube, SoundCloud, ListenBrainz)
2. **Deduplicate** - Songs are deduplicated by artist-title across all sources
3. **Download** - Each song is downloaded using priority order:
   - **Deezer** (FLAC, highest quality) via Telegram bot
   - **Source-native** (YouTube/SoundCloud) as fallback
4. **Process** - `post_download.py` cleans metadata, fetches lyrics, moves to library

## ⚙️ Configuration

Configure in `.env`:

| Variable | Description |
|----------|-------------|
| `INCOMING_DIR` | Staging folder for downloads |
| `MUSIC_DIR` | Main music library |
| `LYRICS_DIR` | Lyrics storage |
| `YOUTUBE_PLAYLIST_URL` | YouTube playlist to monitor |
| `SOUNDCLOUD_PLAYLIST_URL` | SoundCloud URL to monitor |
| `LISTENBRAINZ_PLAYLIST_URL` | ListenBrainz playlist URL |
| `TG_API_ID` | Telegram API ID |
| `TG_API_HASH` | Telegram API Hash |

## 📄 License

MIT License
