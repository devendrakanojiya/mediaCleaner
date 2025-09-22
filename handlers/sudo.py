import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from models import DataManager
from config import ConfigManager
from utils.helpers import get_user_id_from_input, format_user_info

class SudoHandler:
    """Handles sudo user management commands"""
    
    def __init__(self, client: Client, config: ConfigManager, data: DataManager):
        self.client = client
        self.config = config
        self.data = data
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all sudo-related handlers"""
        print("📌 Registering sudo handlers...")
        
        @self.client.on_message(filters.command("addsudo", prefixes=".") & filters.me)
        async def add_sudo_handler(client: Client, message: Message):
            await self.add_sudo(client, message)
        
        @self.client.on_message(filters.command("rmsudo", prefixes=".") & filters.me)
        async def remove_sudo_handler(client: Client, message: Message):
            await self.remove_sudo(client, message)
        
        @self.client.on_message(filters.command("listsudo", prefixes=".") & filters.me)
        async def list_sudo_handler(client: Client, message: Message):
            await self.list_sudo(client, message)
        
        print("✅ Sudo handlers registered")
    
    async def add_sudo(self, client: Client, message: Message):
        """Add a user to sudo list."""
        try:
            # Get user info from message
            user_info = await get_user_id_from_input(client, message)
            if not user_info:
                await message.edit("⚠️ Reply to a user or provide a user ID/username!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            user_id, username, first_name = user_info
            
            # Check if user is owner
            if user_id == self.config.owner_id:
                await message.edit("⚠️ Owner is already privileged!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Check if already in sudo list
            if self.data.is_sudo_user(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"⚠️ User {user_display} is already a sudo user!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Add to sudo list
            if self.data.add_sudo_user(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"✅ Added {user_display} (ID: {user_id}) to sudo users!")
                print(f"🛡️ Added sudo user: {user_display} (ID: {user_id})")
            else:
                await message.edit("❌ Failed to save sudo users!")
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def remove_sudo(self, client: Client, message: Message):
        """Remove a user from sudo list."""
        try:
            # Get user info from message
            user_info = await get_user_id_from_input(client, message)
            if not user_info:
                await message.edit("⚠️ Reply to a user or provide a user ID/username!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            user_id, username, first_name = user_info
            
            # Check if user is in sudo list
            if not self.data.is_sudo_user(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"⚠️ User {user_display} is not a sudo user!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Remove from sudo list
            if self.data.remove_sudo_user(user_id):
                user_display = f"{first_name} (@{username})" if username else first_name
                await message.edit(f"✅ Removed {user_display} (ID: {user_id}) from sudo users!")
                print(f"🛡️ Removed sudo user: {user_display} (ID: {user_id})")
            else:
                await message.edit("❌ Failed to save sudo users!")
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def list_sudo(self, client: Client, message: Message):
        """List all sudo users."""
        try:
            if not self.data.sudo_users:
                await message.edit("📋 No sudo users found!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            sudo_list = "🛡️ **Sudo Users:**\n\n"
            
            for i, user_id in enumerate(self.data.sudo_users, 1):
                try:
                    user = await client.get_users(user_id)
                    user_display = format_user_info(user)
                    sudo_list += f"{i}. {user_display} - ID: `{user_id}`\n"
                except:
                    sudo_list += f"{i}. Unknown User - ID: `{user_id}`\n"
            
            sudo_list += f"\n📊 Total sudo users: {len(self.data.sudo_users)}"
            await message.edit(sudo_list)
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(10)
        await message.delete()
