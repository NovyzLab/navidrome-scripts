import json
import os
import time
import yt_dlp
import sys
import argparse
from typing import List, Dict
import re
from datetime import datetime

# --- Configuration from .env ---
from config import MUSIC_DIR as DOWNLOAD_DIR

# --- Functions ---

def clean_youtube_title(title: str) -> str:
    """
    Cleans up a YouTube video title by removing common metadata.
    """
    # Patterns to remove, including text in parentheses or brackets
    patterns = [
        r'\(.*?\)', r'\[.*?\]', r'ft\..*', r'feat\..*', r'official',
        r'video', r'hd', r'lyrics', r'audio', r'music', r'original',
        r'\+', r'&'
    ]
    cleaned_title = title.lower()
    for pattern in patterns:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE).strip()
    
    # Capitalize the first letter of each word
    return ' '.join(word.capitalize() for word in cleaned_title.split())


def get_songs_from_youtube_playlist(playlist_url: str) -> List[Dict]:
    """
    Fetches a list of songs from a YouTube playlist using yt-dlp.
    It attempts to parse the artist and title from the video's title
    and falls back to the channel name if parsing fails.
    """
    print(f"Fetching songs from YouTube playlist: {playlist_url}...")
    try:
        ydl_opts = {
            'extract_flat': True
        }
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
                    
                    # Remove " - Topic" from artist name
                    if artist.lower().endswith(' - topic'):
                        artist = artist[:-8].strip()

                    # Handle cases where the title is the only thing
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
    """
    Adds artist, title, album, date, and cover art metadata to an audio file.
    """
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TPE1, TIT2, TALB, APIC, TDRC
    except ImportError:
        print("The 'mutagen' library is not installed. Skipping metadata tagging.")
        print("Please install it with: pip install mutagen")
        return False
        
    try:
        audio = MP3(filepath, ID3=ID3)
        
        # Clear any existing ID3 tags to avoid conflicts
        audio.tags.clear()
        
        # Add basic text tags
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TALB(encoding=3, text=title)) # Set album name to the song title
        
        # Add the upload date (formatted as 'YYYY-MM-DD')
        if upload_date:
            audio.tags.add(TDRC(encoding=3, text=upload_date))

        # Add the cover art
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as thumbnail_file:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg', # Assuming the thumbnail is a JPEG
                        type=3, # 3 is the standard for front cover
                        desc=u'Cover',
                        data=thumbnail_file.read()
                    )
                )
            print(f"Successfully embedded cover art from '{os.path.basename(thumbnail_path)}'.")

        audio.save()
        print(f"Successfully added metadata to '{os.path.basename(filepath)}'.")
        return True
    except Exception as e:
        print(f"An error occurred while adding metadata: {e}")
        return False

def download_from_youtube(artist: str, song_title: str, youtube_url: str):
    """
    Downloads the audio directly from a YouTube video URL and adds metadata.
    """
    print(f"Downloading audio from YouTube for: '{artist} - {song_title}'...")
    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Use a cleaner output template to handle the title
    output_template = os.path.join(DOWNLOAD_DIR, f'%(title)s.%(ext)s')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }], #Removed FFmpegMetadata to avoid the ID3 tag already exists error
        'outtmpl': output_template,
        'retries': 5,
        'quiet': True,
        'writethumbnail': True, # This tells yt-dlp to download the thumbnail
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            # Find the actual filename with the correct extension
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            # Find the thumbnail filename
            thumbnail_path = os.path.splitext(filename)[0] + '.webp'
            if not os.path.exists(thumbnail_path):
                 thumbnail_path = os.path.splitext(filename)[0] + '.jpg'
            
            # Get the upload date
            upload_date = info.get('upload_date')
            formatted_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
            
        print(f"Successfully downloaded audio from YouTube for '{song_title}'.")
        
        # Add metadata and cover art to the downloaded file
        add_metadata(mp3_filename, artist, song_title, thumbnail_path, formatted_date)
        
        # Clean up the downloaded thumbnail file
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            
        return True
    except Exception as e:
        print(f"An error occurred while downloading from YouTube: {e}")
        return False

def main():
    """Main function to run the music download workflow with command-line arguments."""
    
    parser = argparse.ArgumentParser(description='Download music from a YouTube playlist.')
    parser.add_argument('--playlist-url', required=True, help='The YouTube playlist URL.')
    
    args = parser.parse_args()
    
    new_songs = get_songs_from_youtube_playlist(args.playlist_url)

    if not new_songs:
        print("No songs to process. Exiting.")
        sys.exit(0)

    for song in new_songs:
        artist = song['artist']
        title = song['title']
        youtube_url = song['youtube_url']
        
        # We don't need a processed songs file for this separate script
        download_from_youtube(artist, title, youtube_url)
        
        print("-" * 20)
        time.sleep(3)

if __name__ == "__main__":
    main()
