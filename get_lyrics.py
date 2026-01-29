import os
import requests
from mutagen import File as MutagenFile

LRCLIB_ENDPOINT = "https://lrclib.net/api/get"

def fetch_synced_lyrics(file_path, lyrics_dir):
    base = os.path.splitext(os.path.basename(file_path))[0]
    music_lrc = os.path.join(os.path.dirname(file_path), base + ".lrc")
    stored_lrc = os.path.join(lyrics_dir, base + ".lrc")

    # Skip if lyrics already exist
    if os.path.exists(music_lrc) or os.path.exists(stored_lrc):
        print(f"Skipping {base}: lyrics already present")
        return

    # Try reading metadata
    try:
        audio = MutagenFile(file_path, easy=True)
    except Exception as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return

    if not audio:
        print(f"Skipping unsupported file: {file_path}")
        return

    artist = (audio.get("artist") or [""])[0]
    title = (audio.get("title") or [""])[0]

    try:
        duration = int(audio.info.length)
    except:
        duration = None

    if not artist or not title:
        print(f"Skipping {file_path}: missing artist/title tags")
        return

    print(f"Searching lyrics for: {artist} - {title}")

    params = {
        "artist_name": artist,
        "track_name": title,
    }
    if duration:
        params["duration"] = duration

    try:
        resp = requests.get(LRCLIB_ENDPOINT, params=params, timeout=8)
    except Exception as e:
        print(f"Request error for {title}: {e}")
        return

    if resp.status_code != 200:
        print(f"Lyrics not found: {artist} - {title}")
        return

    data = resp.json()
    synced = data.get("syncedLyrics")

    if not synced:
        print(f"No synced lyrics available for: {artist} - {title}")
        return

    os.makedirs(lyrics_dir, exist_ok=True)

    try:
        with open(stored_lrc, "w", encoding="utf-8") as f:
            f.write(synced.strip() + "\n")
    except Exception as e:
        print(f"Error writing LRC file for {title}: {e}")
        return

    try:
        if not os.path.exists(music_lrc):
            os.symlink(stored_lrc, music_lrc)
    except:
        pass  # symlink may fail on some systems, not critical

    print(f"Lyrics saved: {base}")


music_dir = "/opt/navidrome/music"
lyrics_dir = "/opt/navidrome/lyrics"

for file in os.listdir(music_dir):
    if file.lower().endswith((".mp3", ".flac")):
        fetch_synced_lyrics(os.path.join(music_dir, file), lyrics_dir)


