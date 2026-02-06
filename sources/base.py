"""
Base classes and data models for the music downloader pipeline.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SourceType(Enum):
    """Enum for different music sources."""
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    LISTENBRAINZ = "listenbrainz"


@dataclass
class Song:
    """
    Unified song representation used across all sources and downloaders.
    """
    artist: str
    title: str
    source: SourceType
    source_id: str                          # Unique ID from source (for tracking)
    source_url: Optional[str] = None        # Original URL (for fallback download)
    extra: Dict[str, Any] = field(default_factory=dict)  # Source-specific metadata
    
    @property
    def key(self) -> str:
        """Generate a unique key for deduplication based on artist - title."""
        return f"{self.artist} - {self.title}"
    
    def __hash__(self):
        return hash(self.key.lower())
    
    def __eq__(self, other):
        if not isinstance(other, Song):
            return False
        return self.key.lower() == other.key.lower()


class SourceBase(ABC):
    """
    Abstract base class for all source fetchers.
    Sources fetch song lists from playlists/users on various platforms.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this source."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """The SourceType enum value for this source."""
        pass
    
    @abstractmethod
    def get_songs(self, url: str) -> List[Song]:
        """
        Fetch songs from the given URL.
        
        Args:
            url: The playlist/user/track URL to fetch from.
            
        Returns:
            List of Song objects found at the URL.
        """
        pass
    
    def is_configured(self) -> bool:
        """
        Check if this source has valid configuration (e.g., URL in .env).
        Override in subclass if source requires specific config.
        """
        return True


def clean_artist_title(text: str) -> str:
    """
    Aggressively clean artist or title text by removing:
    - Collaboration markers (ft., feat., w/, with, &, /)
    - Content in brackets/parentheses
    - Common junk words
    
    Returns only the first part before any collaboration marker.
    """
    import re
    
    # Cutoff at collaboration markers
    cutoff_terms = r'(\s*,\s*|\s*，\s*|\s*[\/\&\\]|\s+and\s+|\s+ft\.?\s*|\s+feat\.?\s*|\s+w\/\s*|\s+with\s*)'
    parts = re.split(cutoff_terms, text, 1, flags=re.IGNORECASE)
    cleaned = parts[0].strip()
    
    # Remove bracketed/parenthesized content
    cleaned = re.sub(r'\(.*?\)|\[.*?\]', '', cleaned).strip()
    
    # Remove common junk patterns
    junk_patterns = [
        r'official\s*(video|audio|music\s*video)?',
        r'lyrics?\s*video',
        r'hd|hq|4k',
        r'free\s*download',
        r'premiere',
        r'exclusive',
    ]
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Clean leftover symbols
    cleaned = re.sub(r'^[–\-–\s]+|[–\-–\s]+$', '', cleaned).strip()
    
    # Capitalize
    return ' '.join(word.capitalize() for word in cleaned.split()) if cleaned else ""
