import requests
import json
import os
import time
import yt_dlp
import sys
import argparse
import re
import tempfile
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import subprocess
import asyncio
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.tl.functions.messages import GetInlineBotResultsRequest
from telethon.tl.types import MessageMediaDocument, InputWebDocument, DocumentAttributeFilename

# Import all necessary mutagen classes to handle different file types
try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen import File
except ImportError:
    print("Error: Mutagen library not found. Please install it with 'pip install mutagen' to run this script.")
    exit(1)

# --- Configuration from .env ---
from config import (
    FAILED_SONGS_FILE,
    PROCESSED_SONGS_FILE,
    DOWNLOAD_DIR,
    USER_AGENT,
    DEEZER_BOT_USERNAME,
    TG_API_ID as API_ID,
    TG_API_HASH as API_HASH,
    TG_SESSION_NAME as SESSION_NAME,
    validate_telegram_config
)

# Custom exception for handling songs not found on Deezer
class SongNotFoundOnDeezerError(Exception):
    pass

# --- Functions ---

def load_processed_songs() -> Dict:
    """Loads the list of processed songs from a JSON file."""
    if not os.path.exists(PROCESSED_SONGS_FILE):
        return {}
    try:
        with open(PROCESSED_SONGS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {PROCESSED_SONGS_FILE} is empty or corrupted. Starting with an empty history.")
        return {}

def save_processed_songs(processed_songs: Dict):
    """Saves the list of processed songs to a JSON file."""
    with open(PROCESSED_SONGS_FILE, 'w') as f:
        json.dump(processed_songs, f, indent=4)

def load_failed_songs() -> List[Dict]:
    """Loads the list of failed songs from a JSON file."""
    if not os.path.exists(FAILED_SONGS_FILE):
        return []
    try:
        with open(FAILED_SONGS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {FAILED_SONGS_FILE} is empty or corrupted. Starting with an empty failed list.")
        return []

def save_failed_songs(failed_songs: List[Dict]):
    """Saves the list of failed songs to a JSON file."""
    with open(FAILED_SONGS_FILE, 'w') as f:
        json.dump(failed_songs, f, indent=4)

def add_failed_song(artist: str, title: str, youtube_url: str):
    """Adds a song to the failed_songs.json list."""
    failed_songs = load_failed_songs()
    song_entry = {'artist': artist, 'title': title, 'youtube_url': youtube_url}
    # Check if a song with the same artist and title already exists
    if not any(d.get('artist') == artist and d.get('title') == title for d in failed_songs):
        failed_songs.append(song_entry)
        save_failed_songs(failed_songs)
        print(f"Added '{artist} - {title}' to the failed songs list for manual review.")


def clean_youtube_title(title: str) -> tuple[str, str]:
    """
    Cleans up a YouTube video title by extracting a clean artist and title.
    It includes aggressive filtering to completely remove any 'Feat.' or 'W/'
    collaboration indicators and all content following them, as well as 
    metadata in parentheses/brackets.

    Args:
        title: The original YouTube video title string.

    Returns:
        A tuple containing the cleaned artist and song title.
    """
    # Define patterns for common separators between artist and title
    separators = [' - ', ' – ', ' -- ', ' | ', ': ']

    # --- Step 1: Split the title into potential artist and song title ---
    artist = ""
    song_title = title

    found_separator = False
    for sep in separators:
        if sep in title:
            # Only split on the FIRST occurrence of the separator
            parts = title.split(sep, 1)
            artist = parts[0].strip()
            song_title = parts[1].strip()
            found_separator = True
            break

    # If no main separator was found, the whole title is the song, artist is unknown
    if not found_separator:
        artist = ""
        song_title = title # Keep the whole title for initial cleaning

    # --- Step 2: Aggressive Cutoff for Features/Collaborations (Case-Insensitive) ---
    
    # Regex pattern to match any of the cutoff terms (and their surrounding spaces/punctuation).
    # This list includes: , / & and ft. feat. w/ with
    # Everything after the collaboration marker will be completely deleted.
    # The first element in the split array will be the desired clean text.
    cutoff_terms = r'(\s*,\s*|\s*[\/\&\\]|\s+and\s+|\s+ft\.?\s*|\s+feat\.?\s*|\s+w\/\s*|\s+with\s*)'
    
    def apply_cutoff(text: str) -> str:
        """Splits text by collaboration markers and returns only the first part."""
        # Use re.split (case-insensitive)
        # We only split once (maxsplit=1) to ensure we cut off everything after the first marker
        parts = re.split(cutoff_terms, text, 1, flags=re.IGNORECASE)
        return parts[0].strip()

    # Apply aggressive cutoff to both artist and song title parts
    artist = apply_cutoff(artist)
    song_title = apply_cutoff(song_title)

    # --- Step 3: Standard Aggressive Cleaning ---
    
    # 3a. Remove all content within parentheses and brackets, including the symbols themselves.
    song_title = re.sub(r'\(.*?\)|\[.*?\]', '', song_title).strip()
    
    # 3b. Remove any extra leading/trailing symbols that might have been left
    artist = re.sub(r'^[–\-–]', '', artist).strip()
    song_title = re.sub(r'^[–\-–]', '', song_title).strip()
    
    # --- Step 4: Capitalization ---
    
    # Helper to ensure capitalization only happens if the string is not empty
    def smart_capitalize(text: str) -> str:
        return ' '.join(word.capitalize() for word in text.split()) if text else ""
        
    artist = smart_capitalize(artist)
    song_title = smart_capitalize(song_title)

    return artist, song_title


async def download_from_deezer_bot(artist: str, song_title: str, download_dir: str) -> Optional[str]:
    """
    Connects to Telegram, searches for a song via the bot, and downloads it.
    
    Args:
        artist: The name of the artist.
        song_title: The title of the song.
        download_dir: The directory to download the song to.
    
    Returns:
        The path to the downloaded file, or None if the download failed.
    
    Raises:
        SongNotFoundOnDeezerError: If the song could not be downloaded via the bot.
    """
    # Clean the title before creating the search query for the bot
    cleaned_song_title = song_title
    
    # Create a simpler search query using the first few words of the title
    shortened_title = ' '.join(cleaned_song_title.split()[:5])
    query = f"{artist} - {shortened_title}"
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    print(f"Attempting to find song on Deezer bot for: '{query}'")
    
    try:
        # Step 1: Get the inline bot result to find the Deezer track ID.
        # Set a short timeout for the inline bot search to prevent hanging.
        try:
            results = await asyncio.wait_for(client(GetInlineBotResultsRequest(
                peer=DEEZER_BOT_USERNAME,
                bot=DEEZER_BOT_USERNAME,
                query=query,
                offset=''
            )), timeout=10) # 10 second timeout for the search request
        except asyncio.TimeoutError:
            raise SongNotFoundOnDeezerError("Timeout while searching on Deezer bot. The bot did not respond in time.")

        if not results.results:
            raise SongNotFoundOnDeezerError("No results found on Deezer.")

        # Step 2: Iterate through the top results and find the best match based on title.
        deezer_url = None
        for result in results.results[:5]:  # Check the top 5 results
            # Clean the Deezer result title for a better match
            cleaned_result_title = result.title
            
            # Handle truncated titles by removing the ellipsis
            cleaned_result_title_no_ellipsis = cleaned_result_title.replace('...', '')
            print(f"Checking result: {cleaned_result_title_no_ellipsis}")
            
            # Now, we only check for the shortened title within the result.
            # The previous artist check was causing valid results to be rejected.
            if shortened_title.lower().strip() in cleaned_result_title_no_ellipsis.lower().strip():
                # The Deezer track ID is typically the last part of the inline result ID.
                track_id = result.id.split('_')[-1]
                deezer_url = f"https://www.deezer.com/track/us/{track_id}"
                break
        
        if not deezer_url:
            raise SongNotFoundOnDeezerError(f"No matching song title found in Deezer search results for '{song_title}'.")
        
        print(f"Deezer track URL found: {deezer_url}. Sending to bot to initiate download...")
        
        # Step 3: Send the Deezer URL to the bot.
        await client.send_message(DEEZER_BOT_USERNAME, deezer_url)
        
        print("Waiting for audio file...")
        
        # Step 4: Wait for the bot's reply with the audio file.
        # We poll for the latest message from the bot for a limited time.
        start_time = time.time()
        downloaded = False
        file_path = None
        while time.time() - start_time < 60:  # Timeout after 60 seconds
            messages = await client.get_messages(DEEZER_BOT_USERNAME, limit=1)
            
            if messages and isinstance(messages[0].media, MessageMediaDocument) and messages[0].file.mime_type.startswith('audio'):
                message = messages[0]
                print("Audio file received. Downloading...")
                
                # Correctly get the filename from the document attributes.
                file_name = None
                for attr in message.document.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        file_name = attr.file_name
                        break
                
                if file_name:
                    file_path = os.path.join(download_dir, file_name)
                    await client.download_media(message, file=file_path)
                    downloaded = True
                    print("Download complete.")
                else:
                    print("Warning: Could not find filename attribute in the document.")

                break
            
            await asyncio.sleep(5)  # Wait 5 seconds before checking again
        
        if not downloaded:
            raise SongNotFoundOnDeezerError("Timeout: Did not receive an audio file from the bot.")
        
        return file_path

    except RPCError as e:
        print(f"Failed to get inline results or send message: {e}")
        raise SongNotFoundOnDeezerError(f"Failed to get inline results or send message: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during the download process: {e}")
        raise e
    finally:
        await client.disconnect()
        print("Telegram client disconnected.")


def get_songs_from_youtube_playlist(playlist_url: str) -> List[Dict]:
    """
    Fetches a list of songs from a YouTube playlist using yt-dlp.
    It attempts to parse the artist and title from the video's title
    and falls back to a more robust title cleaning if necessary.
    """
    print(f"Fetching songs from YouTube playlist: {playlist_url}...")
    try:
        # Use 'extract_flat' to get a list of video entries without full metadata
        # or downloading the videos themselves.
        ydl_opts = {
            'extract_flat': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)

        songs = []
        if 'entries' in info:
            for entry in info['entries']:
                full_title = entry.get('title', 'Unknown Title')
                artist = 'Unknown Artist'
                title = 'Unknown Title'

                # Use the new cleaning function
                artist, title = clean_youtube_title(full_title)

                # Fallback to channel name if no artist was found by the parser
                if not artist:
                    artist = entry.get('channel', 'Unknown Artist')
                    if artist.endswith(' - Topic'):
                        artist = artist[:-8].strip()

                if artist and title:
                    songs.append({'artist': artist, 'title': title, 'youtube_url': f"https://www.youtube.com/watch?v={entry.get('id')}"})

        print(f"Found {len(songs)} songs from YouTube playlist.")
        return songs
    except Exception as e:
        print(f"An error occurred while fetching from YouTube: {e}")
        return []


def get_songs_from_listenbrainz_history(username: str, token: str) -> List[Dict]:
    """
    Fetches a list of songs from a user's ListenBrainz listening history.
    Requires the 'pylistenbrainz' library.
    """
    try:
        from pylistenbrainz import ListenBrainz
    except ImportError:
        print("The 'pylistenbrainz' library is not installed. Please run: pip install pylistenbrainz")
        return []

    print(f"Fetching songs from ListenBrainz history for user: {username}...")
    try:
        client = ListenBrainz(user_token=token)
        listens = client.get_listens(username=username, count=50)
        
        songs = []
        for listen in listens:
            songs.append({
                'artist': listen.artist_name,
                'title': listen.track_name,
            })
        print(f"Found {len(songs)} songs from ListenBrainz history.")
        return songs
    except Exception as e:
        print(f"An error occurred while fetching from ListenBrainz: {e}")
        return []

def get_songs_from_listenbrainz_playlist(playlist_url: str) -> List[Dict]:
    """
    Fetches a list of songs from a specific ListenBrainz playlist using the ListenBrainz API.
    """
    try:
        import requests
        import re
    except ImportError:
        print("The 'requests' library is not installed. Please run: pip install requests")
        return []

    print(f"Fetching songs from ListenBrainz playlist: {playlist_url}...")
    try:
        # Extract the playlist MBID from the URL using a regular expression.
        match = re.search(r'playlist/([a-f0-9-]{36})', playlist_url)
        if not match:
            print("Invalid ListenBrainz playlist URL. Could not find a valid MBID.")
            return []
        
        playlist_mbid = match.group(1)
        api_url = f"https://api.listenbrainz.org/1/playlist/{playlist_mbid}"
        
        print(f"Requesting playlist data from: {api_url}")
        response = requests.get(api_url, headers={'User-Agent': USER_AGENT}, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        
        playlist_data = response.json()
        
        songs = []
        if 'track' in playlist_data.get('playlist', {}):
            for i, item in enumerate(playlist_data['playlist']['track']):
                print(f"DEBUG: Processing track {i+1}. Raw data: {item}")

                # Use the 'creator' key for the artist and 'title' key for the song title
                artist = item.get('creator')
                title = item.get('title')

                # Check for multiple artists and take only the first one
                if artist and ('&' in artist or ' and ' in artist.lower()):
                    if '&' in artist:
                        artist = artist.split('&')[0].strip()
                    else:
                        artist = artist.split(' and ')[0].strip()

                if not artist or not title:
                    print(f"WARNING: Skipping track {i+1} due to missing artist or title.")
                    continue

                songs.append({
                    'artist': artist,
                    'title': title,
                })
        
        print(f"Found {len(songs)} valid songs in the playlist.")
        return songs
    except requests.exceptions.RequestException as e:
        print(f"An HTTP error occurred while fetching the playlist: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while fetching the playlist from ListenBrainz: {e}")
        return []

def main():
    """Main function to run the music download workflow with command-line arguments."""
    
    parser = argparse.ArgumentParser(description='Download music from a selected source.')
    subparsers = parser.add_subparsers(dest='source', required=True, help='The source to fetch songs from.')
    
    # Subparser for ListenBrainz
    listenbrainz_parser = subparsers.add_parser('listenbrainz', help='Download from ListenBrainz history or a specific playlist.')
    # The username and token are required for history but not for public playlists.
    # We will check for their presence later if --playlist-id is not provided.
    listenbrainz_parser.add_argument('--username', required=False, help='The ListenBrainz username.')
    listenbrainz_parser.add_argument('--token', required=False, help='The ListenBrainz user token.')
    listenbrainz_parser.add_argument('--playlist-url', help='The ListenBrainz playlist URL.')

    # Subparser for YouTube
    youtube_parser = subparsers.add_parser('youtube', help='Download from a YouTube playlist.')
    youtube_parser.add_argument('--playlist-url', required=True, help='The YouTube playlist URL.')
    
    args = parser.parse_args()
    
    new_songs = []

    if args.source == 'listenbrainz':
        if args.playlist_url:
            new_songs = get_songs_from_listenbrainz_playlist(args.playlist_url)
        else:
            # If no playlist ID is provided, username and token are mandatory
            if not args.username or not args.token:
                parser.error("The --username and --token arguments are required to fetch from a user's history.")
            new_songs = get_songs_from_listenbrainz_history(args.username, args.token)
            
    elif args.source == 'youtube':
        new_songs = get_songs_from_youtube_playlist(args.playlist_url)

    if not new_songs:
        print("No songs to process. Exiting.")
        sys.exit(0)

    # Get the list of songs already in the download directory
    processed_songs = load_processed_songs()
    
    # Check for Telegram credentials in .env
    if not validate_telegram_config():
        sys.exit(1)
    
    # Initialize a flag to track if any songs were downloaded
    songs_downloaded = False
    
    # Create a temporary folder for this download session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    temp_download_dir = os.path.join(DOWNLOAD_DIR, f"session_{session_id}")
    os.makedirs(temp_download_dir, exist_ok=True)
    print(f"Created temporary download folder: {temp_download_dir}")
        
    for song in new_songs:
        artist = song['artist']
        title = song['title']
        youtube_url = song.get('youtube_url', 'N/A')
        
        # Clean the title early to ensure a consistent key for processed songs.
        cleaned_title = title
        song_key = f"{artist} - {cleaned_title}"
        
        if song_key in processed_songs:
            print(f"Skipping '{song_key}' as it has already been downloaded.")
            continue
            
        try:
            # First, always try to download from the Deezer bot.
            file_path = asyncio.run(download_from_deezer_bot(artist, title, temp_download_dir))
            
            if file_path:
                print(f"Successfully downloaded '{song_key}' from Deezer bot.")
                songs_downloaded = True # Set the flag to true on a successful download
            else:
                raise SongNotFoundOnDeezerError(f"Download for '{song_key}' failed.")

        except SongNotFoundOnDeezerError as e:
            # Only if the song is NOT found on Deezer, add it to the failed list
            print(f"Reason for failing on Deezer: {e}")
            add_failed_song(artist, title, youtube_url)

        except Exception as e:
            # Catch any other unexpected errors and add to failed list
            print(f"An unexpected error occurred: {e}. Adding to failed list.")
            add_failed_song(artist, title, youtube_url)

        # Mark the song as processed using the consistent key
        processed_songs[song_key] = {'timestamp': time.time(), 'status': 'processed'}
        save_processed_songs(processed_songs)
        
        print("-" * 20)
        time.sleep(3)
        
    # After all downloads are complete, run the metadata cleaner script only if songs were downloaded
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
