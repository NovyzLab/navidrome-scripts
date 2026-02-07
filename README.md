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
│   ├── tidaloader.py         # Tidaloader API - FLAC (priority 5)
│   ├── deezer.py             # Deezer bot (Telegram) - FLAC (priority 10)
│   ├── youtube.py            # YouTube direct (yt-dlp) (priority 50)
│   └── soundcloud.py         # SoundCloud direct (yt-dlp) (priority 50)
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
# Edit .env with your playlist URLs and API credentials
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
   - **Tidaloader** (priority 5) - FLAC via Tidal API, downloads directly to library
   - **Deezer** (priority 10) - FLAC via Telegram bot
   - **YouTube/SoundCloud** (priority 50) - Fallback using yt-dlp
4. **Process** - `post_download.py` cleans metadata, fetches lyrics, moves to library
   - *Note: Tidaloader downloads skip post-processing since they go directly to library*

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
| `TIDALOADER_API_URL` | Tidaloader API endpoint |
| `TIDALOADER_AUTH` | HTTP Basic Auth header (e.g., `Basic YWRtaW46...`) |
| `TG_API_ID` | Telegram API ID (for Deezer bot) |
| `TG_API_HASH` | Telegram API Hash |

## 🎵 Adding New Sources

Create a new file in `sources/` implementing `SourceBase`:

```python
from sources.base import SourceBase, Song, SourceType

class MySource(SourceBase):
    @property
    def name(self) -> str:
        return "MySource"
    
    @property
    def source_type(self) -> SourceType:
        return SourceType.YOUTUBE  # or add new type
    
    def get_songs(self, url: str) -> List[Song]:
        # Fetch and return songs
        pass
```

## 🔽 Adding New Downloaders

Create a new file in `downloaders/` implementing `DownloaderBase`:

```python
from downloaders.base import DownloaderBase
from sources.base import Song

class MyDownloader(DownloaderBase):
    @property
    def name(self) -> str:
        return "MyDownloader"
    
    @property
    def priority(self) -> int:
        return 20  # Lower = higher priority
    
    def is_available(self) -> bool:
        return True  # Check if configured
    
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        # Download and return file path
        pass
```

## 📄 License

MIT License
