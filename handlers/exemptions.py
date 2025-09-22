import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message

from models import DataManager
from config import ConfigManager
from utils.helpers import get_user_id_from_input, parse_duration, format_user_info, format_time_left

class ExemptionHandler:
    """Handles temporary exemption commands"""
    
    def __init__(self, client: Client, config: ConfigManager, data: DataManager):
        self.client = client
        self.config = config
        self.data = data
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all exemption-related handlers"""
        print("📌 Registering exemption handlers...")
        
        @self.client.on_message(filters.command("exempt", prefixes=".") & filters.me)
        async def exempt_user_handler(client: Client, message: Message):
            await self.exempt_user(client, message)
        
        @self.client.on_message(filters.command("listexempt", prefixes=".") & filters.me)
        async def list_exemptions_handler(client: Client, message: Message):
            await self.list_exemptions(client, message)
        
        @self.client.on_message(filters.command("rmexempt", prefixes=".") & filters.me)
        async def remove_exemption_handler(client: Client, message: Message):
            await self.remove_exemption(client, message)
        
        print("✅ Exemption handlers registered")
        
    async def exempt_user(self, client: Client, message: Message):
        """Temporarily exempt a user from media deletion."""
        try:
            # Get user info from message
            user_info = await get_user_id_from_input(client, message)
            if not user_info:
                await message.edit("⚠️ Reply to a user or provide a user ID/username!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            user_id, username, first_name = user_info
            
            # Get duration from command
            if message.reply_to_message:
                duration_str = message.command[1] if len(message.command) > 1 else "1h"
            else:
                duration_str = message.command[2] if len(message.command) > 2 else "1h"
            
            # Parse duration
            duration = parse_duration(duration_str)
            if not duration:
                await message.edit("⚠️ Invalid duration! Use format: 1h, 30m, 2d, etc.")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Check if user is owner or sudo
            if user_id == self.config.owner_id:
                await message.edit("⚠️ Owner is already permanently exempted!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            if self.data.is_sudo_user(user_id):
                await message.edit("⚠️ Sudo users are already permanently exempted!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Add exemption
            expiration_time = datetime.now() + duration
            if self.data.add_exemption(user_id, expiration_time):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(
                    f"⏳ Exempted {user_display} (ID: {user_id}) for {duration_str}\n"
                    f"Expires at: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                print(f"⏳ Added temporary exemption for {user_display} (ID: {user_id}) until {expiration_time}")
            else:
                await message.edit("❌ Failed to save exemption!")
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def list_exemptions(self, client: Client, message: Message):
        """List all temporary exemptions."""
        try:
            # Clean up expired exemptions
            self.data.clean_expired_exemptions()
            
            if not self.data.temp_exemptions:
                await message.edit("📋 No active exemptions!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            exempt_list = "⏳ **Temporary Exemptions:**\n\n"
            current_time = datetime.now()
            
            for i, (user_id, exp_time) in enumerate(self.data.temp_exemptions.items(), 1):
                try:
                    user = await client.get_users(user_id)
                    user_display = format_user_info(user)
                    time_left = exp_time - current_time
                    
                    exempt_list += f"{i}. {user_display}\n"
                    exempt_list += f"   ID: `{user_id}`\n"
                    exempt_list += f"   Expires in: {format_time_left(time_left)}\n\n"
                except:
                    exempt_list += f"{i}. Unknown User - ID: `{user_id}`\n"
                    exempt_list += f"   Expires at: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            await message.edit(exempt_list)
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(10)
        await message.delete()
    
    async def remove_exemption(self, client: Client, message: Message):
        """Remove a user's temporary exemption."""
        try:
            # Get user info from message
            user_info = await get_user_id_from_input(client, message)
            if not user_info:
                await message.edit("⚠️ Reply to a user or provide a user ID/username!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            user_id, username, first_name = user_info
            
            # Check if user has exemption
            if not self.data.is_user_exempted(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"⚠️ User {user_display} is not exempted!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Remove exemption
            if self.data.remove_exemption(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"✅ Removed exemption for {user_display} (ID: {user_id})!")
                print(f"⏳ Removed exemption for {user_display} (ID: {user_id})")
            else:
                await message.edit("❌ Failed to save exemptions!")
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
