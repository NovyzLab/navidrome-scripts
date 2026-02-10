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
            
            # Find best match - must verify artist matches
            track = None
            track_id = None
            track_title = ''
            track_artist = ''
            
            wanted_artist = song.artist.lower().strip()
            wanted_title = song.title.lower().strip()
            
            for result in results:
                r_artist = result.get('artist', {}).get('name', '') if isinstance(result.get('artist'), dict) else result.get('artist', '')
                r_title = result.get('title', '')
                r_artist_lower = r_artist.lower().strip()
                r_title_lower = r_title.lower().strip()
                
                # Check artist match: exact, or one contains the other
                artist_match = (
                    wanted_artist == r_artist_lower or
                    wanted_artist in r_artist_lower or
                    r_artist_lower in wanted_artist
                )
                
                if artist_match:
                    track = result
                    track_id = result.get('id')
                    track_title = r_title
                    track_artist = r_artist
                    break
            
            if not track or not track_id:
                # Show what we found for debugging
                top = results[0]
                top_artist = top.get('artist', {}).get('name', '') if isinstance(top.get('artist'), dict) else top.get('artist', '')
                print(f"  No artist match. Top result was: {top_artist} - {top.get('title', '')}")
                raise SongNotFoundError(f"No matching artist for '{song.artist}' on Tidal")
            
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
