import json
import os
from typing import Dict, Any
from .settings import Config, RuntimeConfig

class ConfigManager:
    """Manages runtime configuration persistence and access"""
    
    CONFIG_FILE = "runtime_config.json"
    
    def __init__(self, config: Config):
        self.config = config
        self.runtime_config = self._load_runtime_config()
    
    def _load_runtime_config(self) -> RuntimeConfig:
        """Load runtime configuration from file, or use defaults."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    # Create runtime config from saved values
                    default_runtime = RuntimeConfig.from_defaults(self.config)
                    # Update with saved values
                    for key, value in saved_config.items():
                        if hasattr(default_runtime, key):
                            setattr(default_runtime, key, value)
                    return default_runtime
        except Exception as e:
            print(f"Error loading runtime config: {e}")
        
        return RuntimeConfig.from_defaults(self.config)
    
    def save(self) -> bool:
        """Save current runtime configuration to file."""
        try:
            config_dict = {
                "DELETION_DELAY_SECONDS": self.runtime_config.DELETION_DELAY_SECONDS,
                "STICKER_DELETION_DELAY_SECONDS": self.runtime_config.STICKER_DELETION_DELAY_SECONDS,
                "MAX_DELETIONS_PER_MINUTE": self.runtime_config.MAX_DELETIONS_PER_MINUTE,
                "OWNER_ID": self.runtime_config.OWNER_ID,
                "STICKER_GIF_DELETION_ENABLED": self.runtime_config.STICKER_GIF_DELETION_ENABLED,
                "BOT_ONLY_MODE": self.runtime_config.BOT_ONLY_MODE
            }
            
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving runtime config: {e}")
            return False
    
    def update(self, key: str, value: Any) -> bool:
        """Update a configuration value"""
        if hasattr(self.runtime_config, key):
            setattr(self.runtime_config, key, value)
            return self.save()
        return False
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults from .env file."""
        self.runtime_config = RuntimeConfig.from_defaults(self.config)
        return self.save()
    
    # Convenient getters
    @property
    def delay(self) -> int:
        return self.runtime_config.DELETION_DELAY_SECONDS
    
    @property
    def sticker_delay(self) -> int:
        return self.runtime_config.STICKER_DELETION_DELAY_SECONDS
    
    @property
    def max_deletions(self) -> int:
        return self.runtime_config.MAX_DELETIONS_PER_MINUTE
    
    @property
    def owner_id(self) -> int:
        return self.runtime_config.OWNER_ID
    
    @property
    def is_sticker_deletion_enabled(self) -> bool:
        return self.runtime_config.STICKER_GIF_DELETION_ENABLED
    
    @property
    def is_bot_only_mode(self) -> bool:
        return self.runtime_config.BOT_ONLY_MODE
