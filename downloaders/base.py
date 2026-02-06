"""
Base classes for downloader implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional
import os
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.base import Song


class DownloaderBase(ABC):
    """
    Abstract base class for all downloader implementations.
    Downloaders handle the actual file download from various services.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this downloader."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Priority for this downloader (lower = higher priority).
        Used when multiple downloaders could handle a song.
        Default priorities:
          - Deezer (FLAC): 10
          - YouTube: 50  
          - SoundCloud: 50
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this downloader is configured and available.
        E.g., Deezer requires Telegram credentials.
        """
        pass
    
    @abstractmethod
    async def download(self, song: Song, download_dir: str) -> Optional[str]:
        """
        Download a song to the specified directory.
        
        Args:
            song: The Song object to download.
            download_dir: Directory to save the downloaded file.
            
        Returns:
            Path to the downloaded file, or None if download failed.
        """
        pass
    
    def can_handle(self, song: Song) -> bool:
        """
        Check if this downloader can handle a particular song.
        Override in subclass for source-specific downloaders.
        
        By default, returns True (can try to download any song).
        """
        return True


class DownloadError(Exception):
    """Raised when a download fails."""
    pass


class SongNotFoundError(DownloadError):
    """Raised when a song cannot be found on a service."""
    pass
