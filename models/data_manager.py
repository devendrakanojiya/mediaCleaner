import json
import os
from typing import List, Dict, Optional
from datetime import datetime

class DataManager:
    """Manages persistent data storage for sudo users and exemptions"""
    
    SUDO_FILE = "sudo_users.json"
    EXEMPTIONS_FILE = "temp_exemptions.json"
    
    def __init__(self):
        self.sudo_users = self._load_sudo_users()
        self.temp_exemptions = self._load_exemptions()
    
    # Sudo Users Management
    def _load_sudo_users(self) -> List[int]:
        """Load sudo users from file."""
        try:
            if os.path.exists(self.SUDO_FILE):
                with open(self.SUDO_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading sudo users: {e}")
        return []
    
    def save_sudo_users(self) -> bool:
        """Save sudo users to file."""
        try:
            with open(self.SUDO_FILE, 'w') as f:
                json.dump(self.sudo_users, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving sudo users: {e}")
            return False
    
    def add_sudo_user(self, user_id: int) -> bool:
        """Add a user to sudo list."""
        if user_id not in self.sudo_users:
            self.sudo_users.append(user_id)
            return self.save_sudo_users()
        return False
    
    def remove_sudo_user(self, user_id: int) -> bool:
        """Remove a user from sudo list."""
        if user_id in self.sudo_users:
            self.sudo_users.remove(user_id)
            return self.save_sudo_users()
        return False
    
    def is_sudo_user(self, user_id: int) -> bool:
        """Check if a user is in sudo list."""
        return user_id in self.sudo_users
    
    # Exemptions Management
    def _load_exemptions(self) -> Dict[int, datetime]:
        """Load temporary exemptions from file."""
        try:
            if os.path.exists(self.EXEMPTIONS_FILE):
                with open(self.EXEMPTIONS_FILE, 'r') as f:
                    data = json.load(f)
                    return {int(user_id): datetime.fromisoformat(exp_time) 
                           for user_id, exp_time in data.items()}
        except Exception as e:
            print(f"Error loading exemptions: {e}")
        return {}
    
    def save_exemptions(self) -> bool:
        """Save temporary exemptions to file."""
        try:
            data = {str(user_id): exp_time.isoformat() 
                   for user_id, exp_time in self.temp_exemptions.items()}
            with open(self.EXEMPTIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving exemptions: {e}")
            return False
    
    def add_exemption(self, user_id: int, expiration: datetime) -> bool:
        """Add a temporary exemption for a user."""
        self.temp_exemptions[user_id] = expiration
        return self.save_exemptions()
    
    def remove_exemption(self, user_id: int) -> bool:
        """Remove a user's exemption."""
        if user_id in self.temp_exemptions:
            del self.temp_exemptions[user_id]
            return self.save_exemptions()
        return False
    
    def is_user_exempted(self, user_id: int) -> bool:
        """Check if a user is currently exempted."""
        if user_id in self.temp_exemptions:
            if datetime.now() < self.temp_exemptions[user_id]:
                return True
            else:
                # Exemption expired, remove it
                self.remove_exemption(user_id)
        return False
    
    def clean_expired_exemptions(self) -> List[int]:
        """Remove expired exemptions and return list of cleaned user IDs."""
        current_time = datetime.now()
        expired = [uid for uid, exp_time in self.temp_exemptions.items() 
                  if exp_time < current_time]
        
        for uid in expired:
            del self.temp_exemptions[uid]
        
        if expired:
            self.save_exemptions()
        
        return expired
