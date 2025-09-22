import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from typing import Optional
from datetime import datetime

from config import ConfigManager
from models import DataManager
from utils import RateLimiter, AdminCache
from utils.helpers import get_media_type, get_media_emoji, get_sticker_info, format_user_info


class MediaHandler:
    """Handles media detection and deletion"""
    
    def __init__(self, client: Client, config: ConfigManager, data: DataManager, 
                 rate_limiter: RateLimiter, admin_cache: AdminCache):
        self.client = client
        self.config = config
        self.data = data
        self.rate_limiter = rate_limiter
        self.admin_cache = admin_cache
        self.bot_paused = False
        self.pause_reason = ""
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all media-related handlers"""
        print("📌 Registering media handlers...")
        
        # Main media detection handler - FIXED
        @self.client.on_message(filters.group & ~filters.me)
        async def check_media_handler(client: Client, message: Message):
            await self.check_media(client, message)
        
        # Toggle commands - FIXED
        @self.client.on_message(filters.command("stickertoggle", prefixes=".") & filters.me)
        async def toggle_handler(client: Client, message: Message):
            await self.toggle_sticker_deletion(client, message)
        
        @self.client.on_message(filters.command("stickerstatus", prefixes=".") & filters.me)
        async def status_handler(client: Client, message: Message):
            await self.sticker_deletion_status(client, message)
        
        # Clear command - FIXED
        @self.client.on_message(filters.command("clear", prefixes=".") & filters.me & filters.group)
        async def clear_handler(client: Client, message: Message):
            await self.clear_all_media(client, message)
        
        # Test delete command - FIXED
        @self.client.on_message(filters.command("testdelete", prefixes=".") & filters.me)
        async def test_handler(client: Client, message: Message):
            await self.test_delete(client, message)
        
            # ADD THIS NEW HANDLER
        @self.client.on_message(filters.command("botonly", prefixes=".") & filters.me)
        async def botonly_toggle_handler(client: Client, message: Message):
            await self.toggle_bot_only_mode(client, message)
        
        @self.client.on_message(filters.command("botstatus", prefixes=".") & filters.me)
        async def bot_status_handler(client: Client, message: Message):
            await self.bot_only_status(client, message)

        print("✅ Media handlers registered")
    
    # ADD THESE NEW METHODS
    async def toggle_bot_only_mode(self, client: Client, message: Message):
        """Toggle bot-only deletion mode on/off."""
        current_state = self.config.is_bot_only_mode
        new_state = not current_state
        
        if self.config.update("BOT_ONLY_MODE", new_state):
            status = "✅ ENABLED" if new_state else "❌ DISABLED"
            mode_desc = "only bot messages" if new_state else "all user messages"
            await message.edit(f"🤖 Bot-only mode is now {status}\nDeleting: {mode_desc}")
            print(f"🤖 Bot-only mode toggled to: {status}")
        else:
            await message.edit("❌ Failed to save configuration!")
        
        await asyncio.sleep(3)
        await message.delete()

    async def bot_only_status(self, client: Client, message: Message):
        """Check current bot-only mode status."""
        status = "✅ ENABLED" if self.config.is_bot_only_mode else "❌ DISABLED"
        mode_desc = "only bot messages" if self.config.is_bot_only_mode else "all user messages"
        
        await message.edit(f"🤖 Bot-only mode: {status}\nCurrently deleting: {mode_desc}")
        await asyncio.sleep(5)
        await message.delete()

    async def check_media(self, client: Client, message: Message):
        """Check all group messages for media with rate limiting and permission checking."""
        if self.bot_paused:
            return
        
            # ADD THIS NEW CHECK
        # Check if bot-only mode is enabled
        if self.config.is_bot_only_mode:
            if not message.from_user or not message.from_user.is_bot:
                print("🤖 Bot-only mode: Skipping non-bot user")
                return
            print("🤖 Message from bot detected")

        # Check if message is from privileged users
        if await self._is_privileged_user(message):
            return
        
        # Check temporary exemptions
        if message.from_user and self.data.is_user_exempted(message.from_user.id):
            print(f"⏳ Skipping media from temporarily exempted user @{message.from_user.username} (ID: {message.from_user.id})")
            return
        
        # Determine media type
        media_type = get_media_type(message)
        if not media_type:
            return
        
        # Check if sticker/GIF deletion is disabled
        if media_type in ["sticker", "animation"] and not self.config.is_sticker_deletion_enabled:
            return
        
        # Check admin rights
        if not await self._check_and_cache_admin_rights(message.chat.id, message.chat.title):
            return
        
        # Check rate limit
        if not self.rate_limiter.can_delete(self.config.max_deletions):
            print(f"⚠️ Rate limit reached, skipping deletion")
            return
        
        # Process media deletion
        await self._process_media_deletion(message, media_type)
    
    async def _is_privileged_user(self, message: Message) -> bool:
        """Check if message is from owner or sudo user."""
        if not message.from_user:
            return False
        
        user_id = message.from_user.id
        
        # Check owner
        if user_id == self.config.owner_id:
            print(f"👑 Skipping media from owner (ID: {self.config.owner_id})")
            return True
        
        # Check sudo
        if self.data.is_sudo_user(user_id):
            print(f"🛡️ Skipping media from sudo user @{message.from_user.username} (ID: {user_id})")
            return True
        
        return False
    
    async def _check_and_cache_admin_rights(self, chat_id: int, chat_title: str) -> bool:
        """Check and cache admin rights for a chat."""
        # Check cache first
        has_rights = self.admin_cache.get(chat_id)
        
        if has_rights is None:
            # Not in cache, check actual rights
            has_rights = await self._check_admin_rights(chat_id)
            self.admin_cache.set(chat_id, has_rights)
            
            if not has_rights:
                # Only warn once per chat
                if f"warned_{chat_id}" not in self.admin_cache.cache:
                    print(f"⚠️ No admin/delete rights in '{chat_title}' - skipping all media in this chat")
                    self.admin_cache.set_warned(chat_id)
        
        return has_rights
    # Start admin rights 
    async def _check_admin_rights(self, chat_id: int) -> bool:
        """Check if the user account has admin rights with delete permission."""
        try:
            me = await self.client.get_me()
            member = await self.client.get_chat_member(chat_id, me.id)
            
            status_str = str(member.status).lower()
            
            if "creator" in status_str or member.status == "creator":
                return True
            elif "administrator" in status_str or member.status == "administrator":
                # For admins, check delete permission
                if hasattr(member, 'privileges') and member.privileges:
                    if hasattr(member.privileges, 'can_delete_messages'):
                        return bool(member.privileges.can_delete_messages)
                return True  # Default to True for admins
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking admin rights: {e}")
            return False
    
    # Ends admin rights 
    async def _process_media_deletion(self, message: Message, media_type: str):
        """Process media deletion with appropriate delay."""
        sender = message.from_user.username if message.from_user else "Unknown"
        sender_id = message.from_user.id if message.from_user else "Unknown"
        chat_title = message.chat.title if message.chat else "Unknown"
        
        # Determine delay based on media type
        if media_type in ["sticker", "animation"]:
            base_delay = self.config.sticker_delay
            
            if media_type == "sticker":
                sticker_info = get_sticker_info(message.sticker)
                print(f"🎨 Sticker{sticker_info} detected from @{sender} (ID: {sender_id}) in '{chat_title}'")
            else:
                print(f"🎬 GIF detected from @{sender} (ID: {sender_id}) in '{chat_title}'")
        else:
            base_delay = self.config.delay
        
        # Add random delay
        random_delay = base_delay + random.randint(0, 5)
        
        emoji = get_media_emoji(media_type)
        print(f"{emoji} Scheduling deletion of {media_type} in {random_delay} seconds from @{sender} (ID: {sender_id}) in '{chat_title}'")
        
        await asyncio.sleep(random_delay)
        
        try:
            await message.delete()
            self.rate_limiter.record_deletion()
            print(f"✅ Deleted {media_type} from @{sender} (ID: {sender_id}) in '{chat_title}'")
        except Exception as e:
            print(f"❌ Error deleting {media_type} in '{chat_title}': {e}")
            # Update cache if permission error
            if "MESSAGE_DELETE_FORBIDDEN" in str(e) or "not enough rights" in str(e).lower():
                self.admin_cache.set(message.chat.id, False)
    
    async def toggle_sticker_deletion(self, client: Client, message: Message):
        """Toggle sticker and GIF deletion on/off."""
        current_state = self.config.is_sticker_deletion_enabled
        new_state = not current_state
        
        if self.config.update("STICKER_GIF_DELETION_ENABLED", new_state):
            status = "✅ ENABLED" if new_state else "❌ DISABLED"
            await message.edit(f"🎨 Sticker/GIF deletion is now {status}")
            print(f"🎨 Sticker/GIF deletion toggled to: {status}")
        else:
            await message.edit("❌ Failed to save configuration!")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def sticker_deletion_status(self, client: Client, message: Message):
        """Check current sticker/GIF deletion status."""
        status = "✅ ENABLED" if self.config.is_sticker_deletion_enabled else "❌ DISABLED"
        delay_info = f" (Delay: {self.config.sticker_delay}s)" if self.config.is_sticker_deletion_enabled else ""
        
        await message.edit(f"🎨 Sticker/GIF deletion: {status}{delay_info}")
        await asyncio.sleep(5)
        await message.delete()
    
    async def clear_all_media(self, client: Client, message: Message):
        """Delete all media in current chat (with confirmation)."""
        try:
            # Check if this is a confirmation
            if len(message.command) > 1 and message.command[1].lower() == "confirm":
                # Check admin rights
                if not await self._check_admin_rights(message.chat.id):
                    await message.edit("❌ No admin rights to delete messages in this chat!")
                    await asyncio.sleep(3)
                    await message.delete()
                    return
                
                await message.edit("🗑️ Clearing all media in this chat...")
                
                deleted_count = 0
                async for msg in client.get_chat_history(message.chat.id, limit=1000):
                    if get_media_type(msg):
                        try:
                            await msg.delete()
                            deleted_count += 1
                            if deleted_count % 10 == 0:
                                await asyncio.sleep(1)
                        except:
                            pass
                
                await message.edit(f"✅ Deleted {deleted_count} media messages!")
                print(f"🗑️ Cleared {deleted_count} media messages in {message.chat.title}")
            else:
                # Ask for confirmation
                await message.edit(
                    "⚠️ **WARNING**: This will delete ALL media in this chat!\n"
                    "To confirm, use: `.clear confirm`\n\n"
                    "This action cannot be undone!"
                )
            
            await asyncio.sleep(5)
            await message.delete()
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
            await asyncio.sleep(3)
            await message.delete()
    
    async def test_delete(self, client: Client, message: Message):
        """Test deletion on a specific message."""
        if not message.reply_to_message:
            await message.edit("⚠️ Reply to a message to test deletion!")
            await asyncio.sleep(3)
            await message.delete()
            return
         
        try:
            await message.reply_to_message.delete()
            await message.edit("✅ Successfully deleted the message!")
        except Exception as e:
            await message.edit(f"❌ Cannot delete: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
