import sys
import os
import asyncio
import shutil
import subprocess

from downloaders.soundcloud import SoundCloudDownloader
from sources.base import Song, SourceType

async def test():
    # 1. DOWNLOAD
    dl = SoundCloudDownloader()
    song = Song(
        artist="beansclub",
        title="i'll never find this sound of silence",
        source=SourceType.SOUNDCLOUD,
        source_id="test",
        source_url="https://soundcloud.com/beansclub/illneverfindthissoundofsilence"
    )
    
    test_dir = "/tmp/sc_full_pipeline_test"
    os.makedirs(test_dir, exist_ok=True)
    
    print("1. Downloading...")
    result = await dl.download(song, test_dir)
    
    if not result or not os.path.exists(result):
        print("Download failed.")
        return
        
    print(f"Downloaded to: {result}")
    
    # Check picture block immediately after download
    from mutagen.oggopus import OggOpus
    from mutagen import File
    
    audio1 = File(result)
    print(f"Keys after DL (Mutagen.File): {audio1.keys()}")
    
    # 2. RUN METADATA CLEANER Subprocess (like post_download.py does)
    print("\n2. Running metadata_cleaner.py...")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metadata', 'metadata_cleaner.py')
    subprocess.run([sys.executable, script_path, '--source-dir', test_dir])
    
    # Check picture block after cleaner
    audio2 = File(result)
    print(f"Keys after metadata_cleaner.py: {audio2.keys()}")
    
    # 3. Simulate move to library
    print("\n3. Moving to 'library'...")
    fake_lib = "/tmp/sc_fake_lib"
    os.makedirs(fake_lib, exist_ok=True)
    final_path = os.path.join(fake_lib, os.path.basename(result))
    
    # Ensure it's not already there
    if os.path.exists(final_path):
        os.remove(final_path)
        
    shutil.move(result, final_path)
    print(f"Moved to: {final_path}")
    
    # Check picture block in final file
    audio3 = File(final_path)
    print(f"Keys in final destination: {audio3.keys() if audio3 else 'Could not read file'}")
    
    if audio3 and 'metadata_block_picture' in audio3:
        pic_len = len(audio3['metadata_block_picture'][0])
        print(f"\n✅ SUCCESS: Cover art successfully survived the ENTIRE pipeline! (Size: {pic_len} bytes)")
    else:
        print("\n❌ FAILURE: Cover art was lost somewhere in the pipeline!")

if __name__ == "__main__":
    asyncio.run(test())
