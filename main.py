from pyrogram import Client, filters
import asyncio
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

load_dotenv()

SESSION_STRING = os.getenv("SESSION_STRING")

if SESSION_STRING:
    app = Client(
        "media_cleaner",
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH"),
        session_string=SESSION_STRING
    )
else:
    app = Client(
        "media_cleaner",
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH")
    )

DELAY = int(os.getenv("DELETION_DELAY_SECONDS", "40"))
STICKER_DELAY = int(os.getenv("STICKER_DELETION_DELAY_SECONDS", "360"))  # Default 5 minutes (300 seconds)
STICKER_GIF_DELETION_ENABLED = True  # Default to enabled
OWNER_ID = int(os.getenv("OWNER_ID", "1873281192"))  # Add OWNER_ID environment variable

# Rate limiting
deletion_times = []
MAX_DELETIONS_PER_MINUTE = int(os.getenv("DELETION_DELAY_SECONDS", "20"))  # Adjust based on your needs

# Cache for admin status to avoid repeated API calls
admin_cache = {}
CACHE_DURATION = timedelta(minutes=5)  # Cache admin status for 5 minutes

# Sudo users list stored in a JSON file
SUDO_FILE = "sudo_users.json"

def load_sudo_users():
    """Load sudo users from file."""
    try:
        if os.path.exists(SUDO_FILE):
            with open(SUDO_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading sudo users: {e}")
    return []

def save_sudo_users(sudo_list):
    """Save sudo users to file."""
    try:
        with open(SUDO_FILE, 'w') as f:
            json.dump(sudo_list, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving sudo users: {e}")
        return False

# Initialize sudo users list
SUDO_USERS = load_sudo_users()

# Start 
# Quick Actions variables
BOT_PAUSED = False
PAUSE_REASON = ""
TEMP_EXEMPTIONS = {}  # {user_id: expiration_time}
EXEMPTIONS_FILE = "temp_exemptions.json"

def load_exemptions():
    """Load temporary exemptions from file."""
    try:
        if os.path.exists(EXEMPTIONS_FILE):
            with open(EXEMPTIONS_FILE, 'r') as f:
                data = json.load(f)
                # Convert string timestamps back to datetime objects
                return {int(user_id): datetime.fromisoformat(exp_time) 
                       for user_id, exp_time in data.items()}
    except Exception as e:
        print(f"Error loading exemptions: {e}")
    return {}

def save_exemptions():
    """Save temporary exemptions to file."""
    try:
        # Convert datetime objects to ISO format strings for JSON
        data = {str(user_id): exp_time.isoformat() 
               for user_id, exp_time in TEMP_EXEMPTIONS.items()}
        with open(EXEMPTIONS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving exemptions: {e}")
        return False

# Initialize exemptions
TEMP_EXEMPTIONS = load_exemptions()
# End

async def can_delete():
    """Check if we can delete based on rate limit."""
    now = datetime.now()
    # Remove deletions older than 1 minute
    deletion_times[:] = [t for t in deletion_times if now - t < timedelta(minutes=1)]
    return len(deletion_times) < MAX_DELETIONS_PER_MINUTE


async def check_admin_rights(client, chat_id, force_check=False):
    """Check if the user account has admin rights with delete permission."""
    # Check cache first (unless force_check is True)
    cache_key = f"{chat_id}"
    if not force_check and cache_key in admin_cache:
        cached_time, has_rights = admin_cache[cache_key]
        if datetime.now() - cached_time < CACHE_DURATION:
            return has_rights
    
    try:
        # Get chat info first
        chat = await client.get_chat(chat_id)
        # print(f"🔍 Debug - Checking permissions in: {chat.title}")
        
        # Get my own info
        me = await client.get_me()
        
        # Try to get member info
        try:
            member = await client.get_chat_member(chat_id, me.id)
            # print(f"🔍 Debug - My ID: {me.id}")
            # print(f"🔍 Debug - My username: @{me.username if me.username else 'No username'}")
            # print(f"🔍 Debug - Member object: {member}")
            # print(f"🔍 Debug - Status: {member.status}")
            
            # Check the string representation of status
            status_str = str(member.status).lower()
            # print(f"🔍 Debug - Status string: {status_str}")
            
            # Check different status types (handle both enum and string)
            if "creator" in status_str or member.status == "creator":
                has_delete_rights = True
                # print(f"🔍 Debug - I am the creator, have all rights")
            elif "administrator" in status_str or member.status == "administrator":
                # For user accounts as admin, try different ways to check privileges
                has_delete_rights = True  # Default to True for admins
                
                # Try to access privileges in different ways
                if hasattr(member, 'privileges') and member.privileges:
                    if hasattr(member.privileges, 'can_delete_messages'):
                        has_delete_rights = bool(member.privileges.can_delete_messages)
                        # print(f"🔍 Debug - Admin with delete rights (from privileges): {has_delete_rights}")
                    # else:
                        # print(f"🔍 Debug - Admin (privileges exist but no can_delete_messages attribute)")
                elif hasattr(member, 'can_delete_messages'):
                    has_delete_rights = bool(member.can_delete_messages)
                    # print(f"🔍 Debug - Admin with delete rights (direct attribute): {has_delete_rights}")
                else:
                    print(f"🔍 Debug - Admin (assuming delete rights - no privilege info available)")
            else:
                has_delete_rights = False
                # print(f"🔍 Debug - Not an admin (status: {member.status})")
                
        except Exception as e:
            print(f"🔍 Debug - Error getting member info: {e}")
            # If we can't get member info, try a different approach
            # Try to delete a non-existent message to check permissions
            try:
                await client.delete_messages(chat_id, [999999999])
            except Exception as del_error:
                error_str = str(del_error).lower()
                if "message_ids_empty" in error_str or "message to delete not found" in error_str:
                    # This error means we have permission but message doesn't exist
                    has_delete_rights = True
                    print(f"🔍 Debug - Have delete rights (tested with dummy delete)")
                else:
                    has_delete_rights = False
                    print(f"🔍 Debug - No delete rights (test failed: {del_error})")
        
        # Cache the result
        admin_cache[cache_key] = (datetime.now(), has_delete_rights)
        
        # print(f"🔍 Debug - Final decision: {'Has' if has_delete_rights else 'No'} delete rights")
        return has_delete_rights
        
    except Exception as e:
        print(f"❌ Error in check_admin_rights: {e}")
        admin_cache[cache_key] = (datetime.now(), False)
        return False


@app.on_message(filters.group & ~filters.me)  # Don't process my own messages
async def check_media(client, message):
    """Check all group messages with rate limiting and permission checking."""
        # Check if bot is paused
    if BOT_PAUSED:
        return
    # Skip if message is from owner
    if message.from_user and message.from_user.id == OWNER_ID:
        print(f"👑 Skipping media from owner (ID: {OWNER_ID})")
        return
    
    # Skip if message is from sudo user
    if message.from_user and message.from_user.id in SUDO_USERS:
        print(f"🛡️ Skipping media from sudo user @{message.from_user.username} (ID: {message.from_user.id})")
        return
    
    # Check temporary exemptions
    if message.from_user and message.from_user.id in TEMP_EXEMPTIONS:
        if datetime.now() < TEMP_EXEMPTIONS[message.from_user.id]:
            print(f"⏳ Skipping media from temporarily exempted user @{message.from_user.username} (ID: {message.from_user.id})")
            return
        else:
            # Exemption expired, remove it
            del TEMP_EXEMPTIONS[message.from_user.id]
            save_exemptions()
    
    # Determine media type
    media_type = None
    if message.sticker:
        media_type = "sticker"
    elif message.animation:  # GIFs are detected as animations in Telegram
        media_type = "animation"
    elif message.photo:
        media_type = "photo"
    elif message.video:
        media_type = "video"
    elif message.document:
        media_type = "document"
    elif message.audio:
        media_type = "audio"
    elif message.voice:
        media_type = "voice"
    elif message.video_note:
        media_type = "video_note"
    
    # Skip if not media
    if not media_type:
        return

    # NEW: Check if sticker/GIF deletion is disabled
    if media_type in ["sticker", "animation"] and not STICKER_GIF_DELETION_ENABLED:
        return
    
    sender = message.from_user.username if message.from_user else "Unknown"
    sender_id = message.from_user.id if message.from_user else "Unknown"
    chat_title = message.chat.title if message.chat else "Unknown"
    
    # Check if I have admin rights with delete permission
    if not await check_admin_rights(client, message.chat.id):
        # Only print this once per chat (not for every message)
        cache_key = f"warned_{message.chat.id}"
        if cache_key not in admin_cache:
            print(f"⚠️ No admin/delete rights in '{chat_title}' - skipping all media in this chat")
            admin_cache[cache_key] = (datetime.now(), True)
        return
    
    # Check rate limit
    if not await can_delete():
        print(f"⚠️ Rate limit reached, skipping deletion")
        return
    
    # Determine delay based on media type (stickers and GIFs use STICKER_DELAY)
    if media_type == "sticker" or media_type == "animation":
        base_delay = STICKER_DELAY
        
        if media_type == "sticker":
            # Add emoji to indicate sticker type
            sticker_info = ""
            if message.sticker.is_animated:
                sticker_info = " (animated)"
            elif message.sticker.is_video:
                sticker_info = " (video)"
            else:
                sticker_info = " (static)"
            
            print(f"🎨 Sticker{sticker_info} detected from @{sender} (ID: {sender_id}) in '{chat_title}'")
        else:  # animation/GIF
            print(f"🎬 GIF detected from @{sender} (ID: {sender_id}) in '{chat_title}'")
    else:
        base_delay = DELAY
    
    # Add random delay to appear more human-like
    random_delay = base_delay + random.randint(0, 5)
    
    # Show appropriate emoji based on media type
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
    
    emoji = emoji_map.get(media_type, "📎")
    print(f"{emoji} Scheduling deletion of {media_type} in {random_delay} seconds from @{sender} (ID: {sender_id}) in '{chat_title}'")
    
    await asyncio.sleep(random_delay)
    
    try:
        await message.delete()
        deletion_times.append(datetime.now())
        print(f"✅ Deleted {media_type} from @{sender} (ID: {sender_id}) in '{chat_title}'")
    except Exception as e:
        print(f"❌ Error deleting {media_type} in '{chat_title}': {e}")
        # If deletion fails due to permissions, update cache
        if "MESSAGE_DELETE_FORBIDDEN" in str(e) or "not enough rights" in str(e).lower():
            admin_cache[f"{message.chat.id}"] = (datetime.now(), False)


# Command to clear cache - send .clearcache in any chat
@app.on_message(filters.command("clearcache", prefixes=".") & filters.me)
async def clear_cache(client, message):
    """Clear the admin rights cache."""
    admin_cache.clear()
    await message.edit("✅ Admin rights cache cleared!")
    await asyncio.sleep(3)
    await message.delete()


# Command to check status - send .checkstatus in a group
@app.on_message(filters.command("checkstatus", prefixes=".") & filters.me)
async def check_status(client, message):
    """Check my status in current group."""
    try:
        # Debug chat type
        print(f"🔍 Debug - Chat type: {message.chat.type}")
        print(f"🔍 Debug - Chat title: {message.chat.title if message.chat.title else 'No title'}")
        print(f"🔍 Debug - Chat ID: {message.chat.id}")
        
        # Force check admin rights
        has_rights = await check_admin_rights(client, message.chat.id, force_check=True)
        status_text = "✅ Has admin rights with delete permission" if has_rights else "❌ No admin/delete rights"
        
        # Show current delay settings and owner ID
        delay_info = f"\n⏱️ Media delay: {DELAY}s | Sticker/GIF delay: {STICKER_DELAY}s"

        # Get owner username
        owner_info = "\n👑 Owner: "
        if OWNER_ID != 0:
            try:
                owner_user = await client.get_users(OWNER_ID)
                if owner_user.username:
                    owner_info += f"@{owner_user.username}"
                else:
                    owner_info += f"{owner_user.first_name}"
            except:
                owner_info += f"ID: {OWNER_ID}"
        else:
            owner_info += "Not set"


        sticker_status = f"\n🎨 Sticker/GIF deletion: {'✅ ON' if STICKER_GIF_DELETION_ENABLED else '❌ OFF'}"
        # owner_info = f"\n👑 Owner ID: @freaky_dev"
        # Start
        # In your check_status function, add this line after sticker_status:
        pause_status = f"\n⏸️ Bot Status: {'PAUSED - ' + PAUSE_REASON if BOT_PAUSED else '✅ Running'}"

        # Update the final message.edit to include pause_status:
        # Ends
        sudo_info = f"\n🛡️ Sudo users: {len(SUDO_USERS)}"
        
        await message.edit(f"Status in '{message.chat.title}': {status_text}{delay_info}{sticker_status}{pause_status}{owner_info}{sudo_info}")
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(5)



# Command to test deletion - send .testdelete replying to a message
@app.on_message(filters.command("testdelete", prefixes=".") & filters.me)
async def test_delete(client, message):
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


# Command to add sudo user - send .addsudo replying to a user or with user ID
@app.on_message(filters.command("addsudo", prefixes=".") & filters.me)
async def add_sudo(client, message):
    """Add a user to sudo list."""
    global SUDO_USERS
    
    try:
        # Check if replying to a message
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.username
            first_name = message.reply_to_message.from_user.first_name
        elif len(message.command) > 1:
            # Try to parse user ID from command
            try:
                user_id = int(message.command[1])
                # Try to get user info
                try:
                    user = await client.get_users(user_id)
                    username = user.username
                    first_name = user.first_name
                except:
                    username = None
                    first_name = "Unknown"
            except ValueError:
                await message.edit("⚠️ Invalid user ID! Reply to a user or provide a valid user ID.")
                await asyncio.sleep(3)
                await message.delete()
                return
        else:
            await message.edit("⚠️ Reply to a user or provide a user ID!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Check if user is owner
        if user_id == OWNER_ID:
            await message.edit("⚠️ Owner is already privileged!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Check if already in sudo list
        if user_id in SUDO_USERS:
            await message.edit(f"⚠️ User {first_name} (@{username}) is already a sudo user!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Add to sudo list
        SUDO_USERS.append(user_id)
        if save_sudo_users(SUDO_USERS):
            user_info = f"{first_name} (@{username})" if username else f"{first_name}"
            await message.edit(f"✅ Added {user_info} (ID: {user_id}) to sudo users!")
            print(f"🛡️ Added sudo user: {user_info} (ID: {user_id})")
        else:
            await message.edit("❌ Failed to save sudo users!")
        
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(3)
    await message.delete()


# Command to list sudo users - send .listsudo
@app.on_message(filters.command("listsudo", prefixes=".") & filters.me)
async def list_sudo(client, message):
    """List all sudo users."""
    try:
        if not SUDO_USERS:
            await message.edit("📋 No sudo users found!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        sudo_list = "🛡️ **Sudo Users:**\n\n"
        
        for i, user_id in enumerate(SUDO_USERS, 1):
            try:
                user = await client.get_users(user_id)
                username = f"@{user.username}" if user.username else "No username"
                name = user.first_name or "Unknown"
                sudo_list += f"{i}. {name} ({username}) - ID: `{user_id}`\n"
            except:
                sudo_list += f"{i}. Unknown User - ID: `{user_id}`\n"
        
        sudo_list += f"\n📊 Total sudo users: {len(SUDO_USERS)}"
        await message.edit(sudo_list)
        
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(10)
    await message.delete()


# Command to remove sudo user - send .rmsudo replying to a user or with user ID
@app.on_message(filters.command("rmsudo", prefixes=".") & filters.me)
async def remove_sudo(client, message):
    """Remove a user from sudo list."""
    global SUDO_USERS
    
    try:
        # Check if replying to a message
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.username
            first_name = message.reply_to_message.from_user.first_name
        elif len(message.command) > 1:
            # Try to parse user ID from command
            try:
                user_id = int(message.command[1])
                # Try to get user info
                try:
                    user = await client.get_users(user_id)
                    username = user.username
                    first_name = user.first_name
                except:
                    username = None
                    first_name = "Unknown"
            except ValueError:
                await message.edit("⚠️ Invalid user ID! Reply to a user or provide a valid user ID.")
                await asyncio.sleep(3)
                await message.delete()
                return
        else:
            await message.edit("⚠️ Reply to a user or provide a user ID!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Check if user is in sudo list
        if user_id not in SUDO_USERS:
            await message.edit(f"⚠️ User {first_name} (@{username}) is not a sudo user!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Remove from sudo list
        SUDO_USERS.remove(user_id)
        if save_sudo_users(SUDO_USERS):
            user_info = f"{first_name} (@{username})" if username else f"{first_name}"
            await message.edit(f"✅ Removed {user_info} (ID: {user_id}) from sudo users!")
            print(f"🛡️ Removed sudo user: {user_info} (ID: {user_id})")
        else:
            await message.edit("❌ Failed to save sudo users!")
        
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(3)
    await message.delete()

# Command to toggle sticker/GIF deletion - send .stickertoggle
@app.on_message(filters.command("stickertoggle", prefixes=".") & filters.me)
async def toggle_sticker_deletion(client, message):
    """Toggle sticker and GIF deletion on/off."""
    global STICKER_GIF_DELETION_ENABLED
    
    STICKER_GIF_DELETION_ENABLED = not STICKER_GIF_DELETION_ENABLED
    status = "✅ ENABLED" if STICKER_GIF_DELETION_ENABLED else "❌ DISABLED"
    
    await message.edit(f"🎨 Sticker/GIF deletion is now {status}")
    print(f"🎨 Sticker/GIF deletion toggled to: {status}")
    
    await asyncio.sleep(3)
    await message.delete()


# Command to check sticker/GIF deletion status - send .stickerstatus
@app.on_message(filters.command("stickerstatus", prefixes=".") & filters.me)
async def sticker_deletion_status(client, message):
    """Check current sticker/GIF deletion status."""
    status = "✅ ENABLED" if STICKER_GIF_DELETION_ENABLED else "❌ DISABLED"
    delay_info = f" (Delay: {STICKER_DELAY}s)" if STICKER_GIF_DELETION_ENABLED else ""
    
    await message.edit(f"🎨 Sticker/GIF deletion: {status}{delay_info}")
    
    await asyncio.sleep(5)
    await message.delete()

# Start
# Command to pause bot - send .pause
@app.on_message(filters.command("pause", prefixes=".") & filters.me)
async def pause_bot(client, message):
    """Pause all deletion activities."""
    global BOT_PAUSED, PAUSE_REASON
    
    BOT_PAUSED = True
    PAUSE_REASON = " ".join(message.command[1:]) if len(message.command) > 1 else "Manual pause"
    
    await message.edit(f"⏸️ Bot paused. Reason: {PAUSE_REASON}")
    print(f"⏸️ Bot paused. Reason: {PAUSE_REASON}")
    
    await asyncio.sleep(3)
    await message.delete()


# Command to resume bot - send .resume
@app.on_message(filters.command("resume", prefixes=".") & filters.me)
async def resume_bot(client, message):
    """Resume deletion activities."""
    global BOT_PAUSED, PAUSE_REASON
    
    if not BOT_PAUSED:
        await message.edit("⚠️ Bot is not paused!")
        await asyncio.sleep(2)
        await message.delete()
        return
    
    BOT_PAUSED = False
    await message.edit("▶️ Bot resumed!")
    print(f"▶️ Bot resumed after pause. Previous reason: {PAUSE_REASON}")
    PAUSE_REASON = ""
    
    await asyncio.sleep(3)
    await message.delete()


# Command to clear all media in current chat - send .clear
@app.on_message(filters.command("clear", prefixes=".") & filters.me & filters.group)
async def clear_all_media(client, message):
    """Delete all media in current chat (with confirmation)."""
    try:
        # Check if this is a confirmation
        if len(message.command) > 1 and message.command[1].lower() == "confirm":
            # Check admin rights
            if not await check_admin_rights(client, message.chat.id):
                await message.edit("❌ No admin rights to delete messages in this chat!")
                await asyncio.sleep(3)
                await message.delete()
                return
            
            await message.edit("🗑️ Clearing all media in this chat...")
            
            deleted_count = 0
            # Search for recent messages (last 1000 messages)
            async for msg in client.get_chat_history(message.chat.id, limit=1000):
                # Check if message has media
                if (msg.photo or msg.video or msg.sticker or msg.animation or 
                    msg.document or msg.audio or msg.voice or msg.video_note):
                    try:
                        await msg.delete()
                        deleted_count += 1
                        # Small delay to avoid rate limits
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


# Command to temporarily exempt a user - send .exempt @user 1h
@app.on_message(filters.command("exempt", prefixes=".") & filters.me)
async def exempt_user(client, message):
    """Temporarily exempt a user from media deletion."""
    global TEMP_EXEMPTIONS
    
    try:
        # Check if replying to a message
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            username = message.reply_to_message.from_user.username
            first_name = message.reply_to_message.from_user.first_name
            
            # Get duration from command
            duration_str = message.command[1] if len(message.command) > 1 else "1h"
        elif len(message.command) > 1:
            # Try to parse user ID from command
            try:
                user_id = int(message.command[1])
                # Try to get user info
                try:
                    user = await client.get_users(user_id)
                    username = user.username
                    first_name = user.first_name
                except:
                    username = None
                    first_name = "Unknown"
                
                # Get duration
                duration_str = message.command[2] if len(message.command) > 2 else "1h"
            except ValueError:
                await message.edit("⚠️ Invalid user ID! Reply to a user or provide a valid user ID.")
                await asyncio.sleep(3)
                await message.delete()
                return
        else:
            await message.edit("⚠️ Reply to a user or provide a user ID!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Parse duration
        duration = parse_duration(duration_str)
        if not duration:
            await message.edit("⚠️ Invalid duration! Use format: 1h, 30m, 2d, etc.")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Check if user is owner or sudo
        if user_id == OWNER_ID:
            await message.edit("⚠️ Owner is already permanently exempted!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        if user_id in SUDO_USERS:
            await message.edit("⚠️ Sudo users are already permanently exempted!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        # Add exemption
        expiration_time = datetime.now() + duration
        TEMP_EXEMPTIONS[user_id] = expiration_time
        
        if save_exemptions():
            user_info = f"{first_name} (@{username})" if username else f"{first_name}"
            await message.edit(
                f"⏳ Exempted {user_info} (ID: {user_id}) for {duration_str}\n"
                f"Expires at: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(f"⏳ Added temporary exemption for {user_info} (ID: {user_id}) until {expiration_time}")
        else:
            await message.edit("❌ Failed to save exemption!")
        
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(3)
    await message.delete()


# Helper function to parse duration strings
def parse_duration(duration_str):
    """Parse duration string (e.g., '1h', '30m', '2d') to timedelta."""
    try:
        # Extract number and unit
        import re
        match = re.match(r'(\d+)([smhd])', duration_str.lower())
        if not match:
            return None
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit == 's':
            return timedelta(seconds=amount)
        elif unit == 'm':
            return timedelta(minutes=amount)
        elif unit == 'h':
            return timedelta(hours=amount)
        elif unit == 'd':
            return timedelta(days=amount)
        else:
            return None
    except:
        return None


# Command to list exemptions - send .listexempt
@app.on_message(filters.command("listexempt", prefixes=".") & filters.me)
async def list_exemptions(client, message):
    """List all temporary exemptions."""
    try:
        # Clean up expired exemptions first
        current_time = datetime.now()
        expired = [uid for uid, exp_time in TEMP_EXEMPTIONS.items() if exp_time < current_time]
        for uid in expired:
            del TEMP_EXEMPTIONS[uid]
        
        if expired:
            save_exemptions()
        
        if not TEMP_EXEMPTIONS:
            await message.edit("📋 No active exemptions!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        exempt_list = "⏳ **Temporary Exemptions:**\n\n"
        
        for i, (user_id, exp_time) in enumerate(TEMP_EXEMPTIONS.items(), 1):
            try:
                user = await client.get_users(user_id)
                username = f"@{user.username}" if user.username else "No username"
                name = user.first_name or "Unknown"
                time_left = exp_time - current_time
                hours, remainder = divmod(time_left.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                
                exempt_list += f"{i}. {name} ({username})\n"
                exempt_list += f"   ID: `{user_id}`\n"
                exempt_list += f"   Expires in: {int(hours)}h {int(minutes)}m\n\n"
            except:
                exempt_list += f"{i}. Unknown User - ID: `{user_id}`\n"
                exempt_list += f"   Expires at: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        await message.edit(exempt_list)
        
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(10)
    await message.delete() 
# End

print("Starting media cleaner userbot...")
print(f"⏱️  Media deletion delay: {DELAY} seconds")
print(f"🎨 Sticker/GIF deletion delay: {STICKER_DELAY} seconds")
print(f"👑 Owner ID: {OWNER_ID if OWNER_ID != 0 else 'Not set'}")
print("Commands: addsudo, listsudo, rmsudo, clearcache, checkstatus, testdelete, stickertoggle, stickerstatus, pause, resume, clear, exempt")
app.run()
