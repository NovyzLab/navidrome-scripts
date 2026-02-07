"""
Tidaloader downloader module - downloads FLAC via the Tidaloader API.
Highest priority downloader - downloads directly to library.
"""
import os
import sys
from typing import Optional
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    requests = None

from downloaders.base import DownloaderBase, SongNotFoundError
from sources.base import Song
from config import TIDALOADER_API_URL, TIDALOADER_AUTH


class TidaloaderDownloader(DownloaderBase):
    """
    Downloads FLAC music via Tidaloader API.
    Highest priority - downloads directly to library, skips post-processing.
    """
    
    def __init__(self):
        self.api_url = TIDALOADER_API_URL.rstrip('/') if TIDALOADER_API_URL else ''
        self.auth = TIDALOADER_AUTH
        self.skip_post_processing = True  # Downloads go directly to library
    
    @property
    def name(self) -> str:
        return "Tidaloader"
    
    @property
    def priority(self) -> int:
        return 5  # Highest priority (lower number = higher priority)
    
    def is_available(self) -> bool:
        """Check if API URL and auth are configured."""
        if not requests:
            return False
        if not self.api_url or not self.auth:
            return False
        
        # Optionally check API health
        try:
            response = requests.get(
                f"{self.api_url}/api/health",
                headers=self._get_headers(),
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def _get_headers(self) -> dict:
        """Get request headers with authorization."""
        return {
            'accept': 'application/json',
            'authorization': self.auth,
            'Content-Type': 'application/json',
        }
    
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        """
        Search for track on Tidal and add to download queue.
        Returns True if track was found and queued.
        
        Note: download_dir is ignored since Tidaloader downloads directly to library.
        """
        if not self.is_available():
            return None
        
        # Search for the track
        query = f"{song.artist} {song.title}"
        print(f"  Searching Tidaloader for: {query}")
        
        try:
            response = requests.get(
                f"{self.api_url}/api/search/tracks",
                params={'q': query},
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get('items', [])
            
            # Check if we have results
            if not results:
                raise SongNotFoundError(f"No results on Tidal for '{query}'")
            
            # Find best match (first result is usually best)
            track = results[0]
            track_id = track.get('id')
            track_title = track.get('title', '')
            track_artist = track.get('artist', {}).get('name', '') if isinstance(track.get('artist'), dict) else track.get('artist', '')
            
            if not track_id:
                raise SongNotFoundError("Track found but no ID available")
            
            print(f"  Found: {track_artist} - {track_title} (ID: {track_id})")
            
            # Add to download queue
            queue_item = {
                'track_id': track_id,
                'title': track_title,
                'artist': track_artist,
                'album': track.get('album', {}).get('title', '') if isinstance(track.get('album'), dict) else track.get('album', ''),
                'quality': 'LOSSLESS',  # Request FLAC
            }
            
            queue_response = requests.post(
                f"{self.api_url}/api/queue/add",
                headers=self._get_headers(),
                json={'tracks': [queue_item]},
                timeout=30
            )
            queue_response.raise_for_status()
            
            print(f"  ✓ Added to Tidaloader queue: {track_artist} - {track_title}")
            
            # Return a placeholder path (actual download is handled by server)
            return f"tidaloader://{track_id}"
            
        except requests.exceptions.RequestException as e:
            raise SongNotFoundError(f"API error: {e}")
        except SongNotFoundError:
            raise
        except Exception as e:
            raise SongNotFoundError(f"Error: {e}")
