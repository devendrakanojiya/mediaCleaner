import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Immutable configuration from environment variables"""
    API_ID: int = int(os.getenv("API_ID"))
    API_HASH: str = os.getenv("API_HASH")
    SESSION_STRING: Optional[str] = os.getenv("SESSION_STRING")
    
    # Default values from environment
    DEFAULT_DELETION_DELAY: int = int(os.getenv("DELETION_DELAY_SECONDS", "40"))
    DEFAULT_STICKER_DELAY: int = int(os.getenv("STICKER_DELETION_DELAY_SECONDS", "360"))
    DEFAULT_MAX_DELETIONS: int = int(os.getenv("MAX_DELETIONS_PER_MINUTE", "20"))
    DEFAULT_OWNER_ID: int = int(os.getenv("OWNER_ID", "1873281192"))

@dataclass
class RuntimeConfig:
    """Mutable runtime configuration"""
    DELETION_DELAY_SECONDS: int
    STICKER_DELETION_DELAY_SECONDS: int
    MAX_DELETIONS_PER_MINUTE: int
    OWNER_ID: int
    STICKER_GIF_DELETION_ENABLED: bool = True
    BOT_ONLY_MODE: bool = False  # ADD THIS LINE
    
    @classmethod
    def from_defaults(cls, config: Config) -> 'RuntimeConfig':
        """Create runtime config from default values"""
        return cls(
            DELETION_DELAY_SECONDS=config.DEFAULT_DELETION_DELAY,
            STICKER_DELETION_DELAY_SECONDS=config.DEFAULT_STICKER_DELAY,
            MAX_DELETIONS_PER_MINUTE=config.DEFAULT_MAX_DELETIONS,
            OWNER_ID=config.DEFAULT_OWNER_ID,
            STICKER_GIF_DELETION_ENABLED=True,
            BOT_ONLY_MODE=False  # ADD THIS LINE
        )