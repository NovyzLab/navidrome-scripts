"""
SoundCloud source module - fetches songs from SoundCloud playlists/users/tracks.
"""
import os
import sys
import re
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp not found. Please install with: pip install yt-dlp")
    yt_dlp = None

from sources.base import SourceBase, SourceType, Song, clean_artist_title


class SoundCloudSource(SourceBase):
    """Fetches songs from SoundCloud playlists, users, or individual tracks."""
    
    @property
    def name(self) -> str:
        return "SoundCloud"
    
    @property
    def source_type(self) -> SourceType:
        return SourceType.SOUNDCLOUD
    
    def get_songs(self, url: str) -> List[Song]:
        """
        Fetch songs from a SoundCloud URL.
        Supports playlists, user profiles, and individual tracks.
        """
        if not yt_dlp:
            print("yt-dlp is required for SoundCloud sources")
            return []
        
        print(f"Fetching songs from SoundCloud: {url}...")
        
        try:
            ydl_opts = {
                'extract_flat': 'in_playlist',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            songs = []
            
            # Handle playlist/user (has entries)
            if 'entries' in info:
                for entry in info['entries']:
                    if not entry:
                        continue
                    song = self._extract_song_info(entry)
                    if song:
                        songs.append(song)
            else:
                # Single track
                song = self._extract_song_info(info)
                if song:
                    songs.append(song)
            
            print(f"Found {len(songs)} songs from SoundCloud.")
            return songs
            
        except Exception as e:
            print(f"Error fetching from SoundCloud: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_song_info(self, entry: dict) -> Song | None:
        """Extract artist and title from a SoundCloud track entry."""
        track_url = entry.get('url', entry.get('webpage_url', ''))
        track_id = entry.get('id', track_url)
        
        # Try to get artist from uploader
        uploader = entry.get('uploader', '')
        
        # Get title and parse it
        title = entry.get('title', '')
        
        if not title:
            return None
        
        # Check if title contains "artist - title" format
        artist, song_title = self._parse_title(title, uploader)
        
        if not artist or not song_title:
            return None
        
        return Song(
            artist=artist,
            title=song_title,
            source=self.source_type,
            source_id=str(track_id),
            source_url=track_url,
            extra={
                'uploader': uploader,
                'thumbnail': entry.get('thumbnail', ''),
            }
        )
    
    def _parse_title(self, title: str, uploader: str) -> tuple[str, str]:
        """
        Parse artist and song title from SoundCloud track title.
        Many SoundCloud tracks use "Artist - Title" format.
        """
        separators = [' - ', ' – ', ' — ', ' | ']
        
        artist = ""
        song_title = title
        
        # Try to split on common separators
        for sep in separators:
            if sep in title:
                parts = title.split(sep, 1)
                artist = parts[0].strip()
                song_title = parts[1].strip()
                break
        
        # If no separator found, use uploader as artist
        if not artist:
            artist = uploader
        
        # Clean both parts
        artist = clean_artist_title(artist)
        song_title = clean_artist_title(song_title)
        
        return artist, song_title
