import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from config import ConfigManager
from utils import AdminCache
from utils.helpers import format_user_info

class AdminHandler:
    """Handles admin-related commands and configuration"""
    
    def __init__(self, client: Client, config: ConfigManager, admin_cache: AdminCache):
        self.client = client
        self.config = config
        self.admin_cache = admin_cache
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all admin-related handlers"""
        print("📌 Registering admin handlers...")
        
        # Configuration commands - FIXED
        @self.client.on_message(filters.command("config", prefixes=".") & filters.me)
        async def view_config_handler(client: Client, message: Message):
            await self.view_config(client, message)
        
        @self.client.on_message(filters.command("setconfig", prefixes=".") & filters.me)
        async def set_config_handler(client: Client, message: Message):
            await self.set_config(client, message)
        
        @self.client.on_message(filters.command("resetconfig", prefixes=".") & filters.me)
        async def reset_config_handler(client: Client, message: Message):
            await self.reset_config(client, message)
        
        # Status and cache commands - FIXED
        @self.client.on_message(filters.command("checkstatus", prefixes=".") & filters.me)
        async def check_status_handler(client: Client, message: Message):
            await self.check_status(client, message)
        
        @self.client.on_message(filters.command("clearcache", prefixes=".") & filters.me)
        async def clear_cache_handler(client: Client, message: Message):
            await self.clear_cache(client, message)
        
        print("✅ Admin handlers registered")
    
    async def view_config(self, client: Client, message: Message):
        """View current runtime configuration."""
        try:
            # Get owner info
            owner_info = f"ID: {self.config.owner_id}"
            if self.config.owner_id != 0:
                try:
                    owner_user = await client.get_users(self.config.owner_id)
                    owner_info = format_user_info(owner_user) + f" ({self.config.owner_id})"
                except:
                    pass
            
            config_text = (
                "⚙️ **Current Configuration:**\n\n"
                f"• **Media Delay:** {self.config.delay} seconds\n"
                f"• **Sticker/GIF Delay:** {self.config.sticker_delay} seconds\n"
                f"• **Max Deletions/Min:** {self.config.max_deletions}\n"
                f"• **Owner:** {owner_info}\n"
                f"• **Sticker/GIF Deletion:** {'✅ ON' if self.config.is_sticker_deletion_enabled else '❌ OFF'}\n"
                f"• **Bot-Only Mode:** {'✅ ON (deleting only bot messages)' if self.config.is_bot_only_mode else '❌ OFF (deleting all messages)'}\n\n"  # ADD THIS LINE
                f"📝 Use `.setconfig` to change values"
            )
            
            await message.edit(config_text)
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(7)
        await message.delete()
    
    async def set_config(self, client: Client, message: Message):
        """Set runtime configuration values."""
        try:
            if len(message.command) < 3:
                config_help = (
                    "⚙️ **Configuration Options:**\n\n"
                    "• `delay` - Media deletion delay (seconds)\n"
                    "• `stickerdelay` - Sticker/GIF delay (seconds)\n"
                    "• `maxdeletions` - Max deletions per minute\n"
                    "• `owner` - Owner user ID\n\n"
                    "**Usage:** `.setconfig delay 60`"
                )
                await message.edit(config_help)
                await asyncio.sleep(5)
                await message.delete()
                return
            
            key = message.command[1].lower()
            value = message.command[2]
            
            # Map user-friendly keys to config keys
            key_map = {
                "delay": "DELETION_DELAY_SECONDS",
                "stickerdelay": "STICKER_DELETION_DELAY_SECONDS",
                "maxdeletions": "MAX_DELETIONS_PER_MINUTE",
                "owner": "OWNER_ID"
            }
            
            if key not in key_map:
                await message.edit(f"❌ Unknown config key: {key}")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            config_key = key_map[key]
            
            # Validate and convert value
            try:
                if config_key == "OWNER_ID":
                    # For owner ID, accept username or ID
                    if value.startswith("@"):
                        user = await client.get_users(value)
                        new_value = user.id
                    else:
                        new_value = int(value)
                else:
                    new_value = int(value)
                    if new_value < 1:
                        raise ValueError("Value must be positive")
            except Exception as e:
                await message.edit(f"❌ Invalid value: {e}")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            # Get old value for display
            old_value = getattr(self.config.runtime_config, config_key)
            
            # Update configuration
            if self.config.update(config_key, new_value):
                await message.edit(
                    f"✅ Configuration updated!\n\n"
                    f"**{key}**: {old_value} → {new_value}"
                )
                print(f"⚙️ Config updated: {config_key} = {new_value}")
            else:
                await message.edit("❌ Failed to save configuration!")
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def reset_config(self, client: Client, message: Message):
        """Reset configuration to defaults from .env file."""
        try:
            # Confirm reset
            if len(message.command) > 1 and message.command[1].lower() == "confirm":
                if self.config.reset_to_defaults():
                    await message.edit("✅ Configuration reset to defaults!")
                    print("⚙️ Configuration reset to defaults")
                else:
                    await message.edit("❌ Failed to save configuration!")
            else:
                await message.edit(
                    "⚠️ This will reset all configuration to defaults!\n"
                    "To confirm, use: `.resetconfig confirm`"
                )
            
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def check_status(self, client: Client, message: Message):
        """Check status in current group."""
        try:
            # Debug admin rights
            print(f"🔍 Checking admin rights in chat: {message.chat.title} (ID: {message.chat.id})")
            
            # Force check admin rights with debug
            has_rights = await self._check_admin_rights(client, message.chat.id)
            self.admin_cache.set(message.chat.id, has_rights)
            
            # Additional debug info
            try:
                me = await client.get_me()
                member = await client.get_chat_member(message.chat.id, me.id)
                print(f"🔍 Member status: {member.status}")
            except Exception as e:
                print(f"🔍 Error getting member info: {e}")
            
            status_text = "✅ Has admin rights with delete permission" if has_rights else "❌ No admin/delete rights"
            
            # Rest of the method remains the same...
            delay_info = f"\n⏱️ Media delay: {self.config.delay}s | Sticker/GIF delay: {self.config.sticker_delay}s"
            
            owner_info = "\n👑 Owner: "
            if self.config.owner_id != 0:
                try:
                    owner_user = await client.get_users(self.config.owner_id)
                    owner_info += format_user_info(owner_user)
                except:
                    owner_info += f"ID: {self.config.owner_id}"
            else:
                owner_info += "Not set"
            
            sticker_status = f"\n🎨 Sticker/GIF deletion: {'✅ ON' if self.config.is_sticker_deletion_enabled else '❌ OFF'}"
            bot_only_status = f"\n🤖 Bot-only mode: {'✅ ON' if self.config.is_bot_only_mode else '❌ OFF'}"

            pause_status = ""
            sudo_info = ""
            
            # Try to get MediaHandler status
            for handler in getattr(client, '_custom_handlers', []):
                if hasattr(handler, 'bot_paused'):
                    pause_status = f"\n⏸️ Bot Status: {'PAUSED - ' + handler.pause_reason if handler.bot_paused else '✅ Running'}"
                    break
            
            if hasattr(self, 'data'):
                sudo_info = f"\n🛡️ Sudo users: {len(self.data.sudo_users)}"
            
            await message.edit(
                f"Status in '{message.chat.title}': {status_text}"
                f"{delay_info}{sticker_status}{bot_only_status}{pause_status}{owner_info}{sudo_info}"
            )
        except Exception as e:
            await message.edit(f"❌ Error: {e}")
        
        await asyncio.sleep(5)
        await message.delete()
    # Start Admin Rights 

    async def _check_admin_rights(self, client: Client, chat_id: int) -> bool:
        """Check if the user account has admin rights with delete permission."""
        try:
            me = await client.get_me()
            print(f"🔍 Checking rights for user: {me.first_name} (ID: {me.id})")
            
            member = await client.get_chat_member(chat_id, me.id)
            print(f"🔍 Member status: {member.status} (type: {type(member.status)})")
            
            # Check if creator
            if member.status == "creator" or str(member.status).lower() == "creator":
                print("✅ User is creator - has all rights")
                return True
            
            # Check if administrator
            if member.status == "administrator" or str(member.status).lower() == "administrator":
                print("📋 User is administrator - checking privileges...")
                # For user accounts as admin, check privileges
                if hasattr(member, 'privileges') and member.privileges:
                    print(f"🔍 Privileges object exists: {member.privileges}")
                    if hasattr(member.privileges, 'can_delete_messages'):
                        can_delete = bool(member.privileges.can_delete_messages)
                        print(f"🔍 Can delete messages: {can_delete}")
                        return can_delete
                    else:
                        print("⚠️ can_delete_messages attribute not found, assuming True for admin")
                        return True
                else:
                    print("⚠️ No privileges object found, assuming True for admin")
                    return True
            
            print("❌ User is not creator or administrator")
            
            # If not creator or admin, try a different approach
            # Try to delete a non-existent message to check permissions
            print("🔍 Trying delete permission test...")
            try:
                await client.delete_messages(chat_id, [999999999])
                print("✅ Delete test passed - has permission")
                return True
            except Exception as del_error:
                error_str = str(del_error).lower()
                if "message_ids_empty" in error_str or "message to delete not found" in error_str:
                    # This error means we have permission but message doesn't exist
                    print("✅ Delete test passed - has permission (message not found)")
                    return True
                else:
                    # Any other error means no permission
                    print(f"❌ Delete test failed: {del_error}")
                    return False
            
        except Exception as e:
            print(f"❌ Error checking admin rights: {e}")
            # Try the delete test as a fallback
            print("🔍 Trying fallback delete test...")
            try:
                await client.delete_messages(chat_id, [999999999])
                print("✅ Fallback delete test passed")
                return True
            except Exception as del_error:
                error_str = str(del_error).lower()
                if "message_ids_empty" in error_str or "message to delete not found" in error_str:
                    print("✅ Fallback delete test passed (message not found)")
                    return True
                else:
                    print(f"❌ Fallback delete test failed: {del_error}")
            return False
    
    # Ends Admin Rights 
    async def clear_cache(self, client: Client, message: Message):
        """Clear the admin rights cache."""
        self.admin_cache.clear()
        await message.edit("✅ Admin rights cache cleared!")
        await asyncio.sleep(3)
        await message.delete()
