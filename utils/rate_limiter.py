from datetime import datetime, timedelta
from typing import List

class RateLimiter:
    """Manages rate limiting for message deletions"""
    
    def __init__(self):
        self.deletion_times: List[datetime] = []
    
    def can_delete(self, max_deletions_per_minute: int) -> bool:
        """Check if we can delete based on rate limit."""
        now = datetime.now()
        # Clean up old entries
        self.deletion_times[:] = [
            t for t in self.deletion_times 
            if now - t < timedelta(minutes=1)
        ]
        return len(self.deletion_times) < max_deletions_per_minute
    
    def record_deletion(self):
        """Record a deletion timestamp."""
        self.deletion_times.append(datetime.now())
    
    def get_current_rate(self) -> int:
        """Get current number of deletions in the last minute."""
        now = datetime.now()
        recent_deletions = [
            t for t in self.deletion_times 
            if now - t < timedelta(minutes=1)
        ]
        return len(recent_deletions)
    
    def reset(self):
        """Reset the rate limiter."""
        self.deletion_times.clear()
