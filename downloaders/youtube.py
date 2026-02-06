"""
YouTube downloader module - downloads music directly from YouTube.
"""
import os
import sys
from typing import Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from downloaders.base import DownloaderBase, DownloadError
from sources.base import Song, SourceType


class YouTubeDownloader(DownloaderBase):
    """Downloads music directly from YouTube using yt-dlp."""
    
    @property
    def name(self) -> str:
        return "YouTube"
    
    @property
    def priority(self) -> int:
        return 50  # Lower priority than Deezer
    
    def is_available(self) -> bool:
        """yt-dlp must be installed."""
        return yt_dlp is not None
    
    def can_handle(self, song: Song) -> bool:
        """Can only handle songs with a YouTube URL."""
        return song.source == SourceType.YOUTUBE and song.source_url is not None
    
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        """
        Download audio from YouTube.
        
        Args:
            song: Song with source_url pointing to YouTube.
            download_dir: Directory to save the file.
            
        Returns:
            Path to downloaded file, or None if failed.
        """
        if not self.can_handle(song):
            return None
        
        if not self.is_available():
            return None
        
        print(f"Downloading from YouTube: {song.artist} - {song.title}")
        
        os.makedirs(download_dir, exist_ok=True)
        output_template = os.path.join(download_dir, f'%(title)s.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'outtmpl': output_template,
            'retries': 5,
            'quiet': True,
            'writethumbnail': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song.source_url, download=True)
                filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                
                # Get thumbnail path for metadata
                thumbnail_path = os.path.splitext(filename)[0] + '.webp'
                if not os.path.exists(thumbnail_path):
                    thumbnail_path = os.path.splitext(filename)[0] + '.jpg'
                
                # Add metadata
                upload_date = info.get('upload_date', '')
                if upload_date:
                    formatted_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
                else:
                    formatted_date = None
                
                self._add_metadata(mp3_filename, song.artist, song.title, thumbnail_path, formatted_date)
                
                # Clean up thumbnail
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                
                print(f"Downloaded: {os.path.basename(mp3_filename)}")
                return mp3_filename
                
        except Exception as e:
            print(f"YouTube download failed: {e}")
            return None
    
    def _add_metadata(self, filepath: str, artist: str, title: str, 
                      thumbnail_path: str, upload_date: str = None):
        """Add metadata tags to the downloaded MP3."""
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TPE1, TIT2, TALB, APIC, TDRC
        except ImportError:
            return
        
        try:
            audio = MP3(filepath, ID3=ID3)
            audio.tags.clear()
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TALB(encoding=3, text=title))
            
            if upload_date:
                audio.tags.add(TDRC(encoding=3, text=upload_date))
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as f:
                    audio.tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc='Cover',
                        data=f.read()
                    ))
            
            audio.save()
        except Exception as e:
            print(f"Error adding metadata: {e}")
