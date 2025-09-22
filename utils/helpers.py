import re
from datetime import timedelta
from typing import Optional, Tuple
from pyrogram.types import Message

def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse duration string (e.g., '1h', '30m', '2d') to timedelta."""
    try:
        match = re.match(r'(\d+)([smhd])', duration_str.lower())
        if not match:
            return None
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        unit_map = {
            's': timedelta(seconds=amount),
            'm': timedelta(minutes=amount),
            'h': timedelta(hours=amount),
            'd': timedelta(days=amount)
        }
        
        return unit_map.get(unit)
    except:
        return None

def get_media_type(message: Message) -> Optional[str]:
    """Detect the type of media in a message."""
    if message.sticker:
        return "sticker"
    elif message.animation:  # GIFs are detected as animations
        return "animation"
    elif message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.document:
        return "document"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.video_note:
        return "video_note"
    return None

def format_user_info(user) -> str:
    """Format user information for display."""
    if not user:
        return "Unknown User"
    
    name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "No username"
    
    return f"{name} ({username})"

def get_media_emoji(media_type: str) -> str:
    """Get emoji for media type."""
    emoji_map = {
        "sticker": "🎨",
        "photo": "🖼️",
        "video": "🎥",
        "document": "📄",
        "audio": "🎵",
        "voice": "🎤",
        "video_note": "📹",
        "animation": "🎬"
    }
    return emoji_map.get(media_type, "📎")

def get_sticker_info(sticker) -> str:
    """Get additional info about a sticker."""
    if sticker.is_animated:
        return " (animated)"
    elif sticker.is_video:
        return " (video)"
    else:
        return " (static)"

def format_time_left(time_left: timedelta) -> str:
    """Format remaining time in a human-readable way."""
    total_seconds = int(time_left.total_seconds())
    
    if total_seconds < 0:
        return "Expired"
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:
        parts.append(f"{minutes}m")
    
    return " ".join(parts)

async def get_user_id_from_input(client, message: Message) -> Optional[Tuple[int, str, str]]:
    """Extract user ID from message (reply or command argument).
    Returns: (user_id, username, first_name) or None
    """
    # Check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.username, user.first_name
    
    # Check command arguments
    elif len(message.command) > 1:
        try:
            # Try to parse as user ID
            user_id = int(message.command[1])
            try:
                user = await client.get_users(user_id)
                return user.id, user.username, user.first_name
            except:
                return user_id, None, "Unknown"
        except ValueError:
            # Try to parse as username
            username = message.command[1]
            if username.startswith("@"):
                try:
                    user = await client.get_users(username)
                    return user.id, user.username, user.first_name
                except:
                    pass
    
    return None
