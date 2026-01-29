"""
SoundCloud Music Downloader
Downloads music from SoundCloud playlists/tracks using yt-dlp.
Follows the same pattern as yt_downloader2.py with session-based temp folders.
"""
import json
import os
import time
import yt_dlp
import sys
import argparse
import subprocess
import uuid
from typing import List, Dict
import re
from datetime import datetime

# --- Configuration from .env ---
from config import INCOMING_DIR as DOWNLOAD_DIR

# Tracking file for downloaded SoundCloud tracks
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SC_DOWNLOADED_FILE = os.path.join(SCRIPT_DIR, 'sc_downloaded.json')


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
    Cleans up a SoundCloud track title by removing common metadata.
    """
    patterns = [
        r'\(.*?\)', r'\[.*?\]', r'free download', r'free dl',
        r'out now', r'premiere', r'exclusive',
    ]
    cleaned_title = title
    for pattern in patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE).strip()
    
    # Capitalize the first letter of each word
    return ' '.join(word.capitalize() for word in cleaned_title.split())


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
    """
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TPE1, TIT2, TALB, APIC
    except ImportError:
        print("The 'mutagen' library is not installed. Skipping metadata tagging.")
        return False
        
    try:
        audio = MP3(filepath, ID3=ID3)
        
        # Add ID3 tag if it doesn't exist
        try:
            audio.add_tags()
        except:
            pass  # Tags already exist
        
        # Add basic text tags
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TALB(encoding=3, text=title))  # Set album name to the song title

        # Add the cover art if available
        if thumbnail_path and os.path.exists(thumbnail_path):
            # Determine mime type based on extension
            ext = os.path.splitext(thumbnail_path)[1].lower()
            mime_type = 'image/jpeg'
            if ext == '.png':
                mime_type = 'image/png'
            elif ext == '.webp':
                mime_type = 'image/webp'
            
            with open(thumbnail_path, 'rb') as thumbnail_file:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3,  # Front cover
                        desc=u'Cover',
                        data=thumbnail_file.read()
                    )
                )
            print(f"Embedded cover art from '{os.path.basename(thumbnail_path)}'.")

        audio.save()
        print(f"Added metadata to '{os.path.basename(filepath)}'.")
        return True
    except Exception as e:
        print(f"Error adding metadata: {e}")
        return False


def download_from_soundcloud(artist: str, song_title: str, url: str, download_dir: str):
    """
    Downloads the audio from a SoundCloud URL and adds metadata.
    """
    print(f"Downloading '{artist} - {song_title}'...")
    os.makedirs(download_dir, exist_ok=True)
    
    # Sanitize filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '', f"{artist} - {song_title}")
    output_template = os.path.join(download_dir, f'{safe_title}.%(ext)s')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'retries': 5,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            # Find the thumbnail
            thumbnail_path = None
            for ext in ['.webp', '.jpg', '.jpeg', '.png']:
                potential_thumb = os.path.splitext(filename)[0] + ext
                if os.path.exists(potential_thumb):
                    thumbnail_path = potential_thumb
                    break
        
        print(f"Successfully downloaded '{song_title}'.")
        
        # Add metadata and cover art to the downloaded file
        add_metadata(mp3_filename, artist, song_title, thumbnail_path)
        
        # Clean up the downloaded thumbnail file
        if thumbnail_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        return True
    except Exception as e:
        print(f"Download failed: {e}")
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

    songs_downloaded = False
    
    # Create a temporary folder for this download session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    temp_download_dir = os.path.join(DOWNLOAD_DIR, f"session_{session_id}")
    os.makedirs(temp_download_dir, exist_ok=True)
    print(f"Created temporary download folder: {temp_download_dir}")

    for song in new_songs:
        song_id = song['id']
        if song_id in downloaded_songs:
            print(f"Skipping already downloaded: {song['artist']} - {song['title']}")
            continue

        success = download_from_soundcloud(song['artist'], song['title'], song['url'], temp_download_dir)
        if success:
            songs_downloaded = True
            downloaded_songs[song_id] = {
                'artist': song['artist'],
                'title': song['title'],
                'url': song['url'],
                'downloaded_at': datetime.now().isoformat()
            }
            save_downloaded_songs(downloaded_songs)
        
        print("-" * 20)
        time.sleep(2)  # Be nice to SoundCloud's servers

    # After all downloads are complete, run the post-processing script only if songs were downloaded
    if songs_downloaded:
        print(f"All downloads complete. Running post_download.py for: {temp_download_dir}")
        subprocess.run(['/usr/bin/python3', 'post_download.py', '--source-dir', temp_download_dir])
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
