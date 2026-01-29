import os
import argparse
import requests
from mutagen import File as MutagenFile

# Import paths from config
from config import INCOMING_DIR, MUSIC_DIR, LYRICS_DIR

LRCLIB_ENDPOINT = "https://lrclib.net/api/get"

# Default staging directory from config
DEFAULT_STAGING_DIR = INCOMING_DIR

def fetch_synced_lyrics(file_path, lyrics_dir=LYRICS_DIR, music_dir=MUSIC_DIR):
    base = os.path.splitext(os.path.basename(file_path))[0]

    # permanent storage
    stored_lrc = os.path.join(lyrics_dir, base + ".lrc")
    # symlink location
    music_lrc = os.path.join(music_dir, base + ".lrc")

    # skip if lyrics exist
    if os.path.exists(stored_lrc) or os.path.exists(music_lrc):
        print(f"Skipping {base}: lyrics already present")
        return

    # read metadata
    try:
        audio = MutagenFile(file_path, easy=True)
    except Exception as e:
        print(f"Metadata read error: {file_path} - {e}")
        return

    if not audio:
        print(f"Unsupported file: {file_path}")
        return

    artist = (audio.get("artist") or [""])[0].strip()
    title = (audio.get("title") or [""])[0].strip()

    try:
        duration = int(audio.info.length)
    except:
        duration = None

    if not artist or not title:
        print(f"Skipping {file_path}: missing artist/title")
        return

    print(f"Searching lyrics for: {artist} - {title}")

    params = {"artist_name": artist, "track_name": title}
    if duration:
        params["duration"] = duration

    try:
        resp = requests.get(LRCLIB_ENDPOINT, params=params, timeout=8)
    except Exception as e:
        print(f"HTTP error: {e}")
        return

    if resp.status_code != 200:
        print(f"No lyrics found for: {artist} - {title}")
        return

    data = resp.json()

    synced = data.get("syncedLyrics")
    plain = data.get("plainLyrics")

    # if no synced, fallback to plain
    if synced:
        lyrics_to_write = synced.strip() + "\n"
        print(f"Found synced lyrics: {artist} - {title}")
    elif plain:
        lyrics_to_write = plain.strip() + "\n"
        print(f"Found plain lyrics only: {artist} - {title}")
    else:
        print(f"No lyrics available at all for: {artist} - {title}")
        return

    os.makedirs(lyrics_dir, exist_ok=True)

    # write lyrics file
    try:
        with open(stored_lrc, "w", encoding="utf-8") as f:
            f.write(lyrics_to_write)
    except Exception as e:
        print(f"Failed writing {stored_lrc}: {e}")
        return

    # symlink in music folder
    try:
        if not os.path.exists(music_lrc):
            os.symlink(stored_lrc, music_lrc)
    except Exception as e:
        print(f"Symlink failed (not critical): {e}")

    print(f"Lyrics saved for {base}")


def main():
    parser = argparse.ArgumentParser(description='Fetch and save lyrics for audio files.')
    parser.add_argument('--source-dir', default=DEFAULT_STAGING_DIR,
                        help=f'Source directory containing audio files (default: {DEFAULT_STAGING_DIR})')
    args = parser.parse_args()

    source_dir = args.source_dir
    print(f"Processing lyrics for files in: {source_dir}")

    # process source folder - support multiple audio formats
    audio_extensions = (".mp3", ".flac", ".opus", ".m4a", ".ogg", ".wav", ".aiff", ".aac")
    for file in os.listdir(source_dir):
        if file.lower().endswith(audio_extensions):
            fetch_synced_lyrics(os.path.join(source_dir, file))


if __name__ == "__main__":
    main()
