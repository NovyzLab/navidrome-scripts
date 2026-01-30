"""
SoundCloud Music Downloader
Downloads music from SoundCloud playlists/tracks using yt-dlp.
Follows the same pattern as yt_downloader2.py with session-based temp folders.
Tries Deezer first for better quality, falls back to SoundCloud.
"""
import json
import os
import time
import yt_dlp
import sys
import argparse
import subprocess
import uuid
import asyncio
from typing import List, Dict
import re
from datetime import datetime

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Project root for finding other scripts
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Configuration from .env ---
from config import INCOMING_DIR as DOWNLOAD_DIR, _data_dir, validate_telegram_config

# Import Deezer download function from music_downloader
from music_downloader import download_from_deezer_bot, SongNotFoundOnDeezerError, load_processed_songs

# Tracking file for downloaded SoundCloud tracks (stored in data directory)
SC_DOWNLOADED_FILE = str(_data_dir / 'sc_downloaded.json')


# --- Helper Functions ---

def load_downloaded_songs() -> Dict[str, Dict]:
    """Loads the JSON file of already downloaded songs."""
    if os.path.exists(SC_DOWNLOADED_FILE):
        try:
            with open(SC_DOWNLOADED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {SC_DOWNLOADED_FILE} is corrupted. Starting fresh.")
            return {}
    return {}


def save_downloaded_songs(data: Dict[str, Dict]):
    """Saves the downloaded songs list to sc_downloaded.json."""
    with open(SC_DOWNLOADED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- Main Functions ---

def clean_title(title: str) -> str:
    """
    Cleans up a SoundCloud track title by removing common metadata,
    collaboration markers, and content in brackets/parentheses.
    Uses aggressive filtering for better Deezer search results.
    """
    # --- Step 1: Aggressive Cutoff for Features/Collaborations (Case-Insensitive) ---
    # Regex pattern to match collaboration markers - everything after is deleted
    cutoff_terms = r'(\s*,\s*|\s*[\/\&\\]|\s+and\s+|\s+ft\.?\s*|\s+feat\.?\s*|\s+w\/\s*|\s+with\s*)'
    
    def apply_cutoff(text: str) -> str:
        """Splits text by collaboration markers and returns only the first part."""
        parts = re.split(cutoff_terms, text, 1, flags=re.IGNORECASE)
        return parts[0].strip()

    cleaned_title = apply_cutoff(title)

    # --- Step 2: Remove bracketed/parenthesized content ---
    cleaned_title = re.sub(r'\(.*?\)|\[.*?\]', '', cleaned_title).strip()
    
    # --- Step 3: Remove SoundCloud-specific junk ---
    junk_patterns = [
        r'free download', r'free dl', r'out now', r'premiere', r'exclusive',
    ]
    for pattern in junk_patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE).strip()
    
    # --- Step 4: Clean up any leftover symbols ---
    cleaned_title = re.sub(r'^[–\-–\s]+|[–\-–\s]+$', '', cleaned_title).strip()
    
    # --- Step 5: Capitalize ---
    return ' '.join(word.capitalize() for word in cleaned_title.split()) if cleaned_title else ""


def get_songs_from_soundcloud(url: str) -> List[Dict]:
    """
    Fetches a list of songs from a SoundCloud URL (playlist, user, or single track).
    Uses yt-dlp to extract the information.
    """
    print(f"Fetching songs from SoundCloud: {url}...")
    try:
        # Don't use extract_flat for playlists - we need full metadata
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,  # Get full metadata
            'skip_download': True,  # Don't download, just extract info
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        songs = []
        
        def extract_song_info(entry):
            """Extract artist and title from a track entry."""
            if not entry:
                return None
            
            # Get the uploader (artist) - try multiple fields
            artist = (
                entry.get('artist') or 
                entry.get('uploader') or 
                entry.get('creator') or 
                entry.get('channel') or
                'Unknown Artist'
            )
            
            # Get the title
            original_title = entry.get('title', 'Unknown Title')
            
            # Try to extract artist from title if it contains " - "
            # Common formats: "Artist - Title" or "Artist - Title (feat. Someone)"
            if ' - ' in original_title and artist in ['Unknown Artist', entry.get('uploader', '')]:
                parts = original_title.split(' - ', 1)
                # Only use the split if the first part looks like an artist name
                if len(parts[0]) < 50:  # Artist names are usually short
                    artist = parts[0].strip()
                    original_title = parts[1].strip()
            
            title = clean_title(original_title)
            
            # Get the URL and ID
            track_url = entry.get('webpage_url') or entry.get('url') or ''
            track_id = entry.get('id') or track_url
            
            if not track_url or title == 'Unknown Title':
                return None
            
            return {
                'artist': artist,
                'title': title,
                'url': track_url,
                'id': str(track_id)
            }
        
        # Handle single track vs playlist
        if info.get('_type') == 'playlist' or 'entries' in info:
            # It's a playlist
            entries = info.get('entries', [])
            for entry in entries:
                song_info = extract_song_info(entry)
                if song_info:
                    songs.append(song_info)
        else:
            # Single track
            song_info = extract_song_info(info)
            if song_info:
                songs.append(song_info)
        
        print(f"Found {len(songs)} songs from SoundCloud.")
        return songs
    except Exception as e:
        print(f"An error occurred while fetching from SoundCloud: {e}")
        import traceback
        traceback.print_exc()
        return []


def add_metadata(filepath: str, artist: str, title: str, thumbnail_path: str = None):
    """
    Adds artist, title, and cover art metadata to an audio file.
    Supports MP3, FLAC, M4A, and other formats via mutagen.
    """
    try:
        from mutagen import File as MutagenFile
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC, Picture
        from mutagen.mp4 import MP4, MP4Cover
        from mutagen.id3 import ID3, TPE1, TIT2, TALB, APIC
    except ImportError:
        print("The 'mutagen' library is not installed. Skipping metadata tagging.")
        return False
    
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        # Read thumbnail data if available
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
        
        if ext == '.mp3':
            audio = MP3(filepath, ID3=ID3)
            try:
                audio.add_tags()
            except:
                pass
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TALB(encoding=3, text=title))
            if thumbnail_data:
                audio.tags.add(APIC(encoding=3, mime=thumbnail_mime, type=3, desc='Cover', data=thumbnail_data))
            audio.save()
            
        elif ext == '.flac':
            audio = FLAC(filepath)
            audio['artist'] = artist
            audio['title'] = title
            audio['album'] = title
            if thumbnail_data:
                pic = Picture()
                pic.type = 3  # Front cover
                pic.mime = thumbnail_mime
                pic.desc = 'Cover'
                pic.data = thumbnail_data
                audio.add_picture(pic)
            audio.save()
            
        elif ext in ['.m4a', '.mp4', '.aac']:
            audio = MP4(filepath)
            audio['\xa9ART'] = [artist]
            audio['\xa9nam'] = [title]
            audio['\xa9alb'] = [title]
            if thumbnail_data:
                # MP4 cover art format
                if thumbnail_mime == 'image/png':
                    cover_format = MP4Cover.FORMAT_PNG
                else:
                    cover_format = MP4Cover.FORMAT_JPEG
                audio['covr'] = [MP4Cover(thumbnail_data, imageformat=cover_format)]
            audio.save()
            
        elif ext in ['.opus', '.ogg']:
            # Opus/Ogg requires special handling for cover art
            from mutagen.oggopus import OggOpus
            from mutagen.oggvorbis import OggVorbis
            import base64
            
            if ext == '.opus':
                audio = OggOpus(filepath)
            else:
                audio = OggVorbis(filepath)
            
            audio['artist'] = artist
            audio['title'] = title
            audio['album'] = title
            
            # Add cover art using METADATA_BLOCK_PICTURE
            if thumbnail_data:
                # Create a FLAC-style picture block
                pic = Picture()
                pic.type = 3  # Front cover
                pic.mime = thumbnail_mime
                pic.desc = 'Cover'
                pic.data = thumbnail_data
                
                # Encode as base64 for Ogg container
                picture_data = pic.write()
                encoded_data = base64.b64encode(picture_data).decode('ascii')
                audio['metadata_block_picture'] = [encoded_data]
            
            audio.save()
            
        else:
            # Try generic mutagen file
            audio = MutagenFile(filepath, easy=True)
            if audio is not None:
                audio['artist'] = artist
                audio['title'] = title
                audio['album'] = title
                audio.save()
            else:
                print(f"Unsupported format for metadata: {ext}")
                return False
        
        if thumbnail_data:
            print(f"Embedded cover art from '{os.path.basename(thumbnail_path)}'.")
        print(f"Added metadata to '{os.path.basename(filepath)}'.")
        return True
        
    except Exception as e:
        print(f"Error adding metadata: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_from_soundcloud(artist: str, song_title: str, url: str, download_dir: str):
    """
    Downloads the audio from a SoundCloud URL with best quality.
    Tries to get original file first (could be lossless), falls back to best stream.
    """
    print(f"Downloading '{artist} - {song_title}'...")
    os.makedirs(download_dir, exist_ok=True)
    
    # Sanitize filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '', f"{artist} - {song_title}")
    output_template = os.path.join(download_dir, f'{safe_title}.%(ext)s')
    
    # Try to get original file first (highest quality)
    # Format selection priority:
    # 1. original (lossless if available)
    # 2. best audio quality stream
    ydl_opts = {
        # Prefer original file, then best audio
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'retries': 5,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,
        # Post-processors: only convert if needed for compatibility
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            # Prefer keeping original format, but ensure compatibility
            'preferredcodec': 'best',  # Keep original codec if possible
            'preferredquality': '0',   # 0 = best quality / no re-encoding
        }],
        # Additional options for best quality
        'prefer_free_formats': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the actual downloaded filename
            # yt-dlp might change extension based on format
            base_filename = os.path.splitext(ydl.prepare_filename(info))[0]
            
            # Find the actual downloaded file (could be various extensions)
            actual_file = None
            for ext in ['.flac', '.wav', '.aiff', '.opus', '.m4a', '.mp3', '.ogg', '.webm']:
                potential_file = base_filename + ext
                if os.path.exists(potential_file):
                    actual_file = potential_file
                    break
            
            if not actual_file:
                # Fallback: look for any audio file with the base name
                for f in os.listdir(download_dir):
                    if f.startswith(os.path.basename(base_filename)) and not f.endswith(('.webp', '.jpg', '.jpeg', '.png')):
                        actual_file = os.path.join(download_dir, f)
                        break
            
            if not actual_file:
                print(f"Warning: Could not find downloaded file for '{song_title}'")
                return False
            
            # Get file info for logging
            file_ext = os.path.splitext(actual_file)[1]
            file_size = os.path.getsize(actual_file) / (1024 * 1024)  # MB
            print(f"Downloaded: {os.path.basename(actual_file)} ({file_size:.1f} MB, format: {file_ext})")
            
            # Find the thumbnail
            thumbnail_path = None
            for ext in ['.webp', '.jpg', '.jpeg', '.png']:
                potential_thumb = base_filename + ext
                if os.path.exists(potential_thumb):
                    thumbnail_path = potential_thumb
                    break
        
        # Add metadata and cover art to the downloaded file
        add_metadata(actual_file, artist, song_title, thumbnail_path)
        
        # Clean up the downloaded thumbnail file
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def try_deezer_first(artist: str, song_title: str, download_dir: str) -> bool:
    """
    Attempts to download from Deezer bot first (better quality).
    Returns True if successful, False if we should fall back to SoundCloud.
    """
    try:
        file_path = asyncio.run(download_from_deezer_bot(artist, song_title, download_dir))
        if file_path:
            print(f"✓ Downloaded from Deezer: {artist} - {song_title}")
            return True
        else:
            print(f"✗ Not found on Deezer, falling back to SoundCloud...")
            return False
    except SongNotFoundOnDeezerError:
        print(f"✗ Not found on Deezer, falling back to SoundCloud...")
        return False
    except Exception as e:
        print(f"✗ Deezer error: {e}, falling back to SoundCloud...")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download music from SoundCloud.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a single track
  python sc_downloader.py -l https://soundcloud.com/artist/track-name
  
  # Download a playlist
  python sc_downloader.py -l https://soundcloud.com/artist/sets/playlist-name
  
  # Download all tracks from a user
  python sc_downloader.py -l https://soundcloud.com/artist/tracks
        """
    )
    parser.add_argument('-l', '--url', required=True, help='SoundCloud URL (track, playlist, or user)')
    args = parser.parse_args()
    
    downloaded_songs = load_downloaded_songs()
    new_songs = get_songs_from_soundcloud(args.url)
    
    if not new_songs:
        print("No songs found. Exiting.")
        sys.exit(0)

    # Load processed songs from music_downloader.py to avoid duplicates
    processed_songs = load_processed_songs()
    print(f"Loaded {len(downloaded_songs)} SoundCloud downloads and {len(processed_songs)} processed songs.")

    # Check if Deezer/Telegram is configured
    deezer_available = validate_telegram_config()
    if deezer_available:
        print("Deezer bot available - will try Deezer first for better quality.")
    else:
        print("Deezer bot not configured - downloading directly from SoundCloud.")

    songs_downloaded = False
    
    # Create a temporary folder for this download session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    temp_download_dir = os.path.join(DOWNLOAD_DIR, f"session_{session_id}")
    os.makedirs(temp_download_dir, exist_ok=True)
    print(f"Created temporary download folder: {temp_download_dir}")

    for song in new_songs:
        song_id = song['id']
        artist = song['artist']
        title = song['title']
        song_key = f"{artist} - {title}"
        
        # Check if already downloaded via SoundCloud (by song_id)
        if song_id in downloaded_songs:
            print(f"Skipping already downloaded (SoundCloud): {song_key}")
            continue
        
        # Check if already downloaded via music_downloader.py (by artist - title)
        if song_key in processed_songs:
            print(f"Skipping already downloaded (Deezer/other): {song_key}")
            continue
        success = False
        source = None

        # Try Deezer first if available (better quality)
        if deezer_available:
            success = try_deezer_first(artist, title, temp_download_dir)
            if success:
                source = 'deezer'

        # Fall back to SoundCloud if Deezer failed or not available
        if not success:
            success = download_from_soundcloud(artist, title, song['url'], temp_download_dir)
            if success:
                source = 'soundcloud'

        if success:
            songs_downloaded = True
            downloaded_songs[song_id] = {
                'artist': artist,
                'title': title,
                'url': song['url'],
                'source': source,
                'downloaded_at': datetime.now().isoformat()
            }
            save_downloaded_songs(downloaded_songs)
        
        print("-" * 20)
        time.sleep(2)  # Be nice to servers

    # After all downloads are complete, run the post-processing script only if songs were downloaded
    if songs_downloaded:
        post_download_script = os.path.join(PROJECT_ROOT, 'automation', 'post_download.py')
        print(f"All downloads complete. Running post_download.py for: {temp_download_dir}")
        subprocess.run(['/usr/bin/python3', post_download_script, '--source-dir', temp_download_dir])
    else:
        print("No new songs were downloaded. Skipping metadata cleanup.")
        # Clean up the empty temp folder if no songs were downloaded
        try:
            os.rmdir(temp_download_dir)
            print(f"Removed empty temp folder: {temp_download_dir}")
        except OSError:
            pass  # Folder not empty or already removed


if __name__ == "__main__":
    main()
