import sys
import os
import asyncio

from downloaders.soundcloud import SoundCloudDownloader
from sources.base import Song, SourceType

async def test():
    dl = SoundCloudDownloader()
    
    song = Song(
        artist="Test Artist",
        title="Test Title",
        source=SourceType.SOUNDCLOUD,
        source_id="test",
        source_url="https://soundcloud.com/beansclub/illneverfindthissoundofsilence" # Random valid URL
    )
    result = await dl.download(song, "/tmp/sc_test")
    print(f"Downloaded to {result}")
    
    if result and os.path.exists(result):
        from mutagen.oggopus import OggOpus
        audio = OggOpus(result)
        print("KEYS:", audio.keys())
        if 'metadata_block_picture' in audio:
            print("PIC data present in Mutagen!")
            print("Len:", len(audio['metadata_block_picture'][0]))
        else:
            print("NO PIC in Mutagen!")
            
        # Verify with ffprobe
        print("\nVerifying with ffprobe:")
        os.system(f"ffprobe -v quiet -show_streams -show_format '{result}' | grep -i attached_pic -B 2 -A 2")

asyncio.run(test())
