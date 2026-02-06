"""
YouTube source module - fetches songs from YouTube playlists.
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


class YouTubeSource(SourceBase):
    """Fetches songs from YouTube playlists."""
    
    @property
    def name(self) -> str:
        return "YouTube"
    
    @property
    def source_type(self) -> SourceType:
        return SourceType.YOUTUBE
    
    def get_songs(self, url: str) -> List[Song]:
        """
        Fetch songs from a YouTube playlist URL.
        Parses artist and title from video titles.
        """
        if not yt_dlp:
            print("yt-dlp is required for YouTube sources")
            return []
        
        print(f"Fetching songs from YouTube playlist: {url}...")
        
        try:
            ydl_opts = {'extract_flat': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            songs = []
            if 'entries' in info:
                print(f"  DEBUG: Found {len(info['entries'])} entries in playlist")
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    full_title = entry.get('title', 'Unknown Title')
                    video_id = entry.get('id', '')
                    
                    # Parse artist and title from video title
                    artist, title = self._parse_youtube_title(full_title)
                    
                    # Fallback to channel name if no artist found
                    if not artist:
                        artist = entry.get('channel', 'Unknown Artist')
                        if artist and artist.endswith(' - Topic'):
                            artist = artist[:-8].strip()
                    
                    # If still no artist, use "Unknown Artist"
                    if not artist:
                        artist = 'Unknown Artist'
                    
                    # If no title after cleaning, use original
                    if not title:
                        title = full_title
                    
                    songs.append(Song(
                        artist=artist,
                        title=title,
                        source=self.source_type,
                        source_id=video_id,
                        source_url=f"https://www.youtube.com/watch?v={video_id}",
                        extra={'channel': entry.get('channel', '')}
                    ))
            else:
                print(f"  DEBUG: No 'entries' key in info. Keys: {info.keys()}")
            
            print(f"Found {len(songs)} songs from YouTube playlist.")
            return songs
            
        except Exception as e:
            print(f"Error fetching from YouTube: {e}")
            return []
    
    def _parse_youtube_title(self, title: str) -> tuple[str, str]:
        """
        Parse artist and song title from a YouTube video title.
        Handles common formats like "Artist - Song" and cleans metadata.
        """
        separators = [' - ', ' – ', ' -- ', ' | ', ': ']
        
        artist = ""
        song_title = title
        
        # Try to split on common separators
        for sep in separators:
            if sep in title:
                parts = title.split(sep, 1)
                artist = parts[0].strip()
                song_title = parts[1].strip()
                break
        
        # Clean both parts
        artist = clean_artist_title(artist)
        song_title = clean_artist_title(song_title)
        
        return artist, song_title
