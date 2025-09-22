from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

class AdminCache:
    """Caches admin status to avoid repeated API calls"""
    
    def __init__(self, cache_duration: timedelta = timedelta(minutes=5)):
        self.cache: Dict[str, Tuple[datetime, bool]] = {}
        self.cache_duration = cache_duration
    
    def get(self, chat_id: int, force_check: bool = False) -> Optional[bool]:
        """Get cached admin status for a chat."""
        if force_check:
            return None
            
        cache_key = str(chat_id)
        if cache_key in self.cache:
            cached_time, has_rights = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return has_rights
        return None
    
    def set(self, chat_id: int, has_rights: bool):
        """Cache admin status for a chat."""
        cache_key = str(chat_id)
        self.cache[cache_key] = (datetime.now(), has_rights)
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
    
    def clear_chat(self, chat_id: int):
        """Clear cache for a specific chat."""
        cache_key = str(chat_id)
        if cache_key in self.cache:
            del self.cache[cache_key]
    
    def get_warned_chats(self) -> set:
        """Get set of chat IDs that have been warned about no admin rights."""
        warned = set()
        for key, (timestamp, has_rights) in self.cache.items():
            if key.startswith("warned_") and has_rights:
                chat_id = key.replace("warned_", "")
                warned.add(chat_id)
        return warned
    
    def set_warned(self, chat_id: int):
        """Mark a chat as warned about no admin rights."""
        cache_key = f"warned_{chat_id}"
        self.cache[cache_key] = (datetime.now(), True)
