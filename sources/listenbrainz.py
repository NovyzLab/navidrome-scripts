"""
ListenBrainz source module - fetches songs from ListenBrainz playlists.
"""
import os
import sys
import re
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    print("Error: requests not found. Please install with: pip install requests")
    requests = None

from sources.base import SourceBase, SourceType, Song, clean_artist_title
from config import USER_AGENT


class ListenBrainzSource(SourceBase):
    """Fetches songs from ListenBrainz playlists."""
    
    @property
    def name(self) -> str:
        return "ListenBrainz"
    
    @property
    def source_type(self) -> SourceType:
        return SourceType.LISTENBRAINZ
    
    def get_songs(self, url: str) -> List[Song]:
        """
        Fetch songs from a ListenBrainz playlist URL.
        """
        if not requests:
            print("requests library is required for ListenBrainz sources")
            return []
        
        print(f"Fetching songs from ListenBrainz playlist: {url}...")
        
        try:
            # Extract the playlist MBID from the URL
            match = re.search(r'playlist/([a-f0-9-]{36})', url)
            if not match:
                print("Invalid ListenBrainz playlist URL. Could not find a valid MBID.")
                return []
            
            playlist_mbid = match.group(1)
            api_url = f"https://api.listenbrainz.org/1/playlist/{playlist_mbid}"
            
            print(f"Requesting playlist data from: {api_url}")
            response = requests.get(
                api_url,
                headers={'User-Agent': USER_AGENT},
                timeout=10
            )
            response.raise_for_status()
            
            playlist_data = response.json()
            songs = []
            
            if 'track' in playlist_data.get('playlist', {}):
                for item in playlist_data['playlist']['track']:
                    artist = item.get('creator', '')
                    title = item.get('title', '')
                    
                    if not artist or not title:
                        continue
                    
                    # Clean artist (handle multiple artists)
                    artist = clean_artist_title(artist)
                    
                    # Get recording MBID if available
                    recording_mbid = ''
                    if 'identifier' in item:
                        for ident in item['identifier']:
                            if 'musicbrainz.org/recording/' in ident:
                                mbid_match = re.search(r'recording/([a-f0-9-]{36})', ident)
                                if mbid_match:
                                    recording_mbid = mbid_match.group(1)
                                    break
                    
                    songs.append(Song(
                        artist=artist,
                        title=title,
                        source=self.source_type,
                        source_id=recording_mbid or f"{artist}-{title}",
                        source_url=None,  # No direct URL for ListenBrainz tracks
                        extra={'recording_mbid': recording_mbid}
                    ))
            
            print(f"Found {len(songs)} songs from ListenBrainz playlist.")
            return songs
            
        except requests.exceptions.RequestException as e:
            print(f"HTTP error fetching ListenBrainz playlist: {e}")
            return []
        except Exception as e:
            print(f"Error fetching from ListenBrainz: {e}")
            return []
