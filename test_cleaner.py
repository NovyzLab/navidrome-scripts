import sys
import os
import asyncio
from mutagen import File
import re

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
    
    result = await dl.download(song, "/tmp/sc_test2")
    
    if result:
        print(f"Downloaded: {result}")
        
        # Now run the cleaner logic on it
        audio = File(result)
        tags_modified = False
        all_artists = set()
        
        # Check if picture starts correctly
        if 'metadata_block_picture' in audio:
            print("BEFORE CLEANER: Picture block exists.")
        else:
            print("BEFORE CLEANER: No picture block :(")
        
        # Extract artists
        for tag_name in ('artist', 'main_artist'):
            tag = audio.get(tag_name)
            if tag and isinstance(tag, list):
                for artist in tag:
                    cleaned_artist = re.sub(
                        r'(\s+ft\.|\s+feat\.|\s*\/|\s*&|\s+and\s*|\s*,|\s*，).+',
                        '', artist, flags=re.IGNORECASE
                    ).strip()
                    if cleaned_artist:
                        all_artists.add(cleaned_artist)
        
        # Consolidate artist
        if all_artists:
            final_artist = ", ".join(sorted(all_artists))
            current_artist = audio.get('artist')
            if current_artist != [final_artist]:
                audio['artist'] = [final_artist]
                tags_modified = True
                
        # Remove unwanted
        unwanted_tags = ['main_artist', 'composer', 'performer']
        for tag in unwanted_tags:
            if tag in audio:
                del audio[tag]
                tags_modified = True
                
        tags_modified = True
        
        if tags_modified:
            print("Tags modified, saving...")
            audio.save()
            print("Saved.")
            
        # Re-verify picture block
        audio2 = File(result)
        if 'metadata_block_picture' in audio2:
            print("AFTER CLEANER: Picture block survived! ✅")
        else:
            print("AFTER CLEANER: PICTURE BLOCK WAS DELETED BY MUTAGEN! ❌")

if __name__ == "__main__":
    asyncio.run(test())
