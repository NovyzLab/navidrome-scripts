"""
Deezer downloader module - downloads music via Telegram Deezer bot.
Provides high quality FLAC downloads when available.
"""
import os
import sys
import time
import asyncio
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename
    from telethon.tl.functions.messages import GetInlineBotResultsRequest
    from telethon.errors.rpcerrorlist import RPCError
except ImportError:
    TelegramClient = None

from downloaders.base import DownloaderBase, SongNotFoundError
from sources.base import Song
from config import (
    TG_API_ID as API_ID,
    TG_API_HASH as API_HASH,
    TG_SESSION_PATH as SESSION_NAME,
    DEEZER_BOT_USERNAME,
    validate_telegram_config
)


class DeezerDownloader(DownloaderBase):
    """Downloads music via Telegram Deezer bot (high quality FLAC)."""
    
    @property
    def name(self) -> str:
        return "Deezer"
    
    @property
    def priority(self) -> int:
        return 10  # Highest priority (best quality)
    
    def is_available(self) -> bool:
        """Check if Telegram credentials are configured."""
        if TelegramClient is None:
            return False
        return validate_telegram_config()
    
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        """
        Download a song via the Deezer Telegram bot.
        
        Args:
            song: The Song object to download.
            download_dir: Directory to save the file.
            
        Returns:
            Path to downloaded file, or None if failed.
        """
        if not self.is_available():
            return None
        
        # Create search query
        shortened_title = ' '.join(song.title.split()[:5])
        query = f"{song.artist} - {shortened_title}"
        
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.start()
        
        print(f"Searching Deezer for: '{query}'")
        
        try:
            # Search via inline bot
            try:
                results = await asyncio.wait_for(
                    client(GetInlineBotResultsRequest(
                        peer=DEEZER_BOT_USERNAME,
                        bot=DEEZER_BOT_USERNAME,
                        query=query,
                        offset=''
                    )),
                    timeout=10
                )
            except asyncio.TimeoutError:
                raise SongNotFoundError("Deezer bot timeout")
            
            if not results.results:
                raise SongNotFoundError("No results on Deezer")
            
            # Find best matching result
            deezer_url = None
            for result in results.results[:5]:
                cleaned_title = result.title.replace('...', '')
                if shortened_title.lower().strip() in cleaned_title.lower().strip():
                    track_id = result.id.split('_')[-1]
                    deezer_url = f"https://www.deezer.com/track/us/{track_id}"
                    break
            
            if not deezer_url:
                raise SongNotFoundError(f"No match found for '{song.title}'")
            
            print(f"Found Deezer track: {deezer_url}")
            
            # Send URL to bot
            await client.send_message(DEEZER_BOT_USERNAME, deezer_url)
            
            # Wait for audio file
            start_time = time.time()
            file_path = None
            
            while time.time() - start_time < 60:
                messages = await client.get_messages(DEEZER_BOT_USERNAME, limit=1)
                
                if messages and isinstance(messages[0].media, MessageMediaDocument):
                    if messages[0].file.mime_type.startswith('audio'):
                        message = messages[0]
                        
                        # Get filename
                        file_name = None
                        for attr in message.document.attributes:
                            if isinstance(attr, DocumentAttributeFilename):
                                file_name = attr.file_name
                                break
                        
                        if file_name:
                            file_path = os.path.join(download_dir, file_name)
                            await client.download_media(message, file=file_path)
                            print(f"Downloaded: {file_name}")
                            return file_path
                
                await asyncio.sleep(5)
            
            raise SongNotFoundError("Timeout waiting for Deezer download")
            
        except RPCError as e:
            raise SongNotFoundError(f"Telegram error: {e}")
        finally:
            await client.disconnect()
