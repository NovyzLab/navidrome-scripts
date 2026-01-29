import json
import os
import time
import yt_dlp
import sys
import argparse
import subprocess
from typing import List, Dict
import re
from datetime import datetime

# --- Configuration ---
DOWNLOAD_DIR = '/opt/navidrome/incoming/'
DOWNLOADED_FILE = 'yt_downloaded.json'


# --- Helper Functions ---

def load_downloaded_songs() -> Dict[str, Dict]:
    """Loads the JSON file of already downloaded songs."""
    if os.path.exists(DOWNLOADED_FILE):
        with open(DOWNLOADED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_downloaded_songs(data: Dict[str, Dict]):
    """Saves the downloaded songs list to yt_downloaded.json."""
    with open(DOWNLOADED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- Main Functions ---

def clean_youtube_title(title: str) -> str:
    patterns = [
        r'\(.*?\)', r'\[.*?\]', r'ft\..*', r'feat\..*', r'official',
        r'video', r'hd', r'lyrics', r'audio', r'music', r'original',
        r'\+', r'&'
    ]
    cleaned_title = title.lower()
    for pattern in patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE).strip()
    return ' '.join(word.capitalize() for word in cleaned_title.split())


def get_songs_from_youtube_playlist(playlist_url: str) -> List[Dict]:
    print(f"Fetching songs from YouTube playlist: {playlist_url}...")
    try:
        ydl_opts = {'extract_flat': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        
        songs = []
        if 'entries' in info:
            for entry in info['entries']:
                if 'title' in entry and 'url' in entry:
                    title_parts = entry['title'].split(' - ', 1)
                    if len(title_parts) == 2:
                        artist = clean_youtube_title(title_parts[0])
                        title = clean_youtube_title(title_parts[1])
                    else:
                        artist = entry.get('channel', 'Unknown Artist')
                        title = clean_youtube_title(entry['title'])
                    if artist.lower().endswith(' - topic'):
                        artist = artist[:-8].strip()
                    if not artist:
                        artist = 'Unknown Artist'
                    songs.append({
                        'artist': artist,
                        'title': title,
                        'youtube_url': entry['url']
                    })
        print(f"Found {len(songs)} songs from YouTube playlist.")
        return songs
    except Exception as e:
        print(f"An error occurred while fetching from YouTube: {e}")
        return []


def add_metadata(filepath: str, artist: str, title: str, thumbnail_path: str, upload_date: str):
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TPE1, TIT2, TALB, APIC, TDRC
    except ImportError:
        print("The 'mutagen' library is not installed. Skipping metadata tagging.")
        return False
        
    try:
        audio = MP3(filepath, ID3=ID3)
        audio.tags.clear()
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TALB(encoding=3, text=title))
        if upload_date:
            audio.tags.add(TDRC(encoding=3, text=upload_date))
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumbnail_file:
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=thumbnail_file.read()))
            print(f"Embedded cover art from '{os.path.basename(thumbnail_path)}'.")
        audio.save()
        print(f"Added metadata to '{os.path.basename(filepath)}'.")
        return True
    except Exception as e:
        print(f"Error adding metadata: {e}")
        return False


def download_from_youtube(artist: str, song_title: str, youtube_url: str):
    print(f"Downloading '{artist} - {song_title}'...")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output_template = os.path.join(DOWNLOAD_DIR, f'%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': output_template,
        'retries': 5,
        'quiet': True,
        'writethumbnail': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            thumbnail_path = os.path.splitext(filename)[0] + '.webp'
            if not os.path.exists(thumbnail_path):
                thumbnail_path = os.path.splitext(filename)[0] + '.jpg'
            upload_date = info.get('upload_date')
            formatted_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
        add_metadata(mp3_filename, artist, song_title, thumbnail_path, formatted_date)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Download music from a YouTube playlist.')
    parser.add_argument('--playlist-url', required=True, help='The YouTube playlist URL.')
    args = parser.parse_args()
    
    downloaded_songs = load_downloaded_songs()
    new_songs = get_songs_from_youtube_playlist(args.playlist_url)
    if not new_songs:
        print("No songs found. Exiting.")
        sys.exit(0)

    songs_downloaded = False

    for song in new_songs:
        song_id = song['youtube_url']
        if song_id in downloaded_songs:
            print(f"Skipping already downloaded: {song['artist']} - {song['title']}")
            continue

        success = download_from_youtube(song['artist'], song['title'], song_id)
        if success:
            songs_downloaded = True
            downloaded_songs[song_id] = {
                'artist': song['artist'],
                'title': song['title'],
                'downloaded_at': datetime.now().isoformat()
            }
            save_downloaded_songs(downloaded_songs)
        
        print("-" * 20)
        time.sleep(3)

    # After all downloads are complete, run the metadata cleaner script only if songs were downloaded
    if songs_downloaded:
        print("All downloads complete. Running metadata_cleaner.py...")
        subprocess.run(['/usr/bin/python3', 'post_download.py'])
    else:
        print("No new songs were downloaded. Skipping metadata cleanup.")


if __name__ == "__main__":
    main()
