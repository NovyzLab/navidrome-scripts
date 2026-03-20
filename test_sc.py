import sys
import os
import asyncio

from downloaders.soundcloud import SoundCloudDownloader
from sources.base import Song, SourceType

async def test():
    dl = SoundCloudDownloader()
    song = Song(
        artist="beansclub",
        title="i'll never find this sound of silence",
        source=SourceType.SOUNDCLOUD,
        source_id="test",
        source_url="https://soundcloud.com/beansclub/illneverfindthissoundofsilence"
    )
    
    print("Testing SoundCloud Downloader...")
    result = await dl.download(song, "testdir")
    
    if result and os.path.exists(result):
        print(f"\nDownload completed: {result}")
        print("\nChecking for embedded cover art...")
        
        try:
            from mutagen.oggopus import OggOpus
            audio = OggOpus(result)
            
            if 'metadata_block_picture' in audio:
                print("✅ YES! Found metadata_block_picture in the Opus file!")
                # Print a bit of the base64 string
                pic_data = audio['metadata_block_picture'][0]
                print(f"   Cover art embedded successfully (Length: {len(pic_data)} bytes)")
            else:
                print("❌ NO cover art found in metadata_block_picture!")
                print("Current keys:", audio.keys())
        except Exception as e:
            print(f"Error reading metadata: {e}")
    else:
        print("\nDownload failed or file not found.")

if __name__ == "__main__":
    asyncio.run(test())
