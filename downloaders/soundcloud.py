"""
SoundCloud downloader module - downloads music from SoundCloud.
"""
import os
import sys
import base64
import glob
from urllib.parse import urlparse
from urllib.request import urlopen
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from downloaders.base import DownloaderBase
from sources.base import Song, SourceType


class SoundCloudDownloader(DownloaderBase):
    """Downloads music directly from SoundCloud using yt-dlp."""
    
    @property
    def name(self) -> str:
        return "SoundCloud"
    
    @property
    def priority(self) -> int:
        return 50  # Same as YouTube (fallback)
    
    def is_available(self) -> bool:
        """yt-dlp must be installed."""
        return yt_dlp is not None
    
    def can_handle(self, song: Song) -> bool:
        """Can only handle songs with a SoundCloud URL."""
        return song.source == SourceType.SOUNDCLOUD and song.source_url is not None
    
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        """
        Download audio from SoundCloud.
        
        Args:
            song: Song with source_url pointing to SoundCloud.
            download_dir: Directory to save the file.
            
        Returns:
            Path to downloaded file, or None if failed.
        """
        if not self.can_handle(song):
            return None
        
        if not self.is_available():
            return None
        
        print(f"Downloading from SoundCloud: {song.artist} - {song.title}")
        
        os.makedirs(download_dir, exist_ok=True)
        safe_title = "".join(c for c in song.title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_artist = "".join(c for c in song.artist if c.isalnum() or c in (' ', '-', '_')).strip()
        output_template = os.path.join(download_dir, f'{safe_artist} - {safe_title}.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'retries': 5,
            'quiet': True,
            'writethumbnail': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'opus',
                    'preferredquality': '0',  # Best quality
                }
            ],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song.source_url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Find the actual downloaded file
                base_name = os.path.splitext(filename)[0]
                opus_file = base_name + '.opus'
                
                if not os.path.exists(opus_file):
                    # Try other extensions
                    for ext in ['.mp3', '.m4a', '.ogg']:
                        if os.path.exists(base_name + ext):
                            opus_file = base_name + ext
                            break
                
                if not os.path.exists(opus_file):
                    print(f"Could not find downloaded file")
                    return None
                
                # Find whatever thumbnail yt-dlp produced via glob.
                thumbnail_path = None
                
                # Try both the exact base name and a looser artist prefix; some yt-dlp
                # versions use different thumbnail naming for SoundCloud.
                potential_thumbs = []
                potential_thumbs.extend(glob.glob(base_name + ".*"))
                potential_thumbs.extend(glob.glob(os.path.join(download_dir, f"{safe_artist}*.*")))
                
                # Filter strictly for standard image extensions
                potential_thumbs = [p for p in potential_thumbs if p.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.jfif'))]
                potential_thumbs = list(dict.fromkeys(potential_thumbs))
                
                # Ultimate fallback: if yt-dlp did not write a thumbnail file, manually
                # download one from any thumbnail-like URL in the metadata.
                thumbnail_url = self._extract_thumbnail_url(info)
                if not potential_thumbs and thumbnail_url:
                    print(f"  yt-dlp thumbnail skipped. Manually downloading {thumbnail_url}...")
                    try:
                        manual_path = self._download_thumbnail_fallback(
                            thumbnail_url,
                            download_dir,
                            safe_artist,
                            safe_title
                        )
                        if manual_path:
                            potential_thumbs.append(manual_path)
                    except Exception as e:
                        print(f"  Failed manual download: {e}")
                
                if potential_thumbs:
                    thumbnail_path = potential_thumbs[0]
                    print(f"  Found thumbnail: {os.path.basename(thumbnail_path)}")
                else:
                    print(f"  ❌ No thumbnail found at all! Searched for {base_name}.*")
                
                # Add metadata
                self._add_metadata(opus_file, song.artist, song.title, thumbnail_path)
                
                # Clean up thumbnail
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
                
                print(f"Downloaded: {os.path.basename(opus_file)}")
                return opus_file
                
        except Exception as e:
            print(f"SoundCloud download failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _add_metadata(self, filepath: str, artist: str, title: str, thumbnail_path: str = None):
        """Add metadata to the downloaded file."""
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            from mutagen import File as MutagenFile
            from mutagen.flac import Picture
        except ImportError:
            return
        
        try:
            # Read thumbnail data
            thumbnail_data = None
            thumbnail_mime = 'image/jpeg'
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumb_ext = os.path.splitext(thumbnail_path)[1].lower()
                if thumb_ext == '.png':
                    thumbnail_mime = 'image/png'
                elif thumb_ext == '.webp':
                    thumbnail_mime = 'image/webp'
                with open(thumbnail_path, 'rb') as f:
                    thumbnail_data = f.read()
            
            if ext in ['.opus', '.ogg']:
                from mutagen.oggopus import OggOpus
                from mutagen.oggvorbis import OggVorbis
                
                if ext == '.opus':
                    audio = OggOpus(filepath)
                else:
                    audio = OggVorbis(filepath)
                
                audio['artist'] = artist
                audio['title'] = title
                audio['album'] = title
                
                if thumbnail_data:
                    pic = Picture()
                    pic.type = 3
                    pic.mime = thumbnail_mime
                    pic.desc = 'Cover'
                    pic.data = thumbnail_data
                    
                    picture_data = pic.write()
                    encoded_data = base64.b64encode(picture_data).decode('ascii')
                    audio['metadata_block_picture'] = [encoded_data]
                
                audio.save()
            else:
                # Generic fallback
                audio = MutagenFile(filepath, easy=True)
                if audio:
                    audio['artist'] = artist
                    audio['title'] = title
                    audio['album'] = title
                    audio.save()
                    
        except Exception as e:
            print(f"Error adding metadata: {e}")

    def _extract_thumbnail_url(self, info: dict) -> Optional[str]:
        """Find the best available thumbnail URL from yt-dlp metadata."""
        direct_thumbnail = info.get('thumbnail')
        if direct_thumbnail:
            return direct_thumbnail

        thumbnails = info.get('thumbnails')
        if isinstance(thumbnails, list) and thumbnails:
            for entry in reversed(thumbnails):
                if isinstance(entry, dict) and entry.get('url'):
                    return entry['url']

        artwork_url = info.get('artwork_url')
        if artwork_url:
            return artwork_url

        return None

    def _download_thumbnail_fallback(
        self,
        thumbnail_url: str,
        download_dir: str,
        safe_artist: str,
        safe_title: str,
    ) -> Optional[str]:
        """Download a fallback thumbnail when yt-dlp doesn't write one."""
        parsed = urlparse(thumbnail_url)
        extension = os.path.splitext(parsed.path)[1].lower()
        if extension not in ('.jpg', '.jpeg', '.png', '.webp', '.jfif'):
            extension = '.jpg'

        manual_path = os.path.join(download_dir, f"{safe_artist} - {safe_title}_fallback{extension}")
        with urlopen(thumbnail_url, timeout=10) as response:
            data = response.read()
            if not data:
                return None
            with open(manual_path, 'wb') as f:
                f.write(data)
        return manual_path
