from pyrogram import Client, filters
import asyncio
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Client(
    "media_cleaner",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH")
)

DELAY = int(os.getenv("DELETION_DELAY_SECONDS", "40"))
STICKER_DELAY = int(os.getenv("STICKER_DELETION_DELAY_SECONDS", "360"))  # Default 5 minutes (300 seconds)
OWNER_ID = int(os.getenv("OWNER_ID", "1873281192"))  # Add OWNER_ID environment variable

# Rate limiting
deletion_times = []
MAX_DELETIONS_PER_MINUTE = int(os.getenv("DELETION_DELAY_SECONDS", "20"))  # Adjust based on your needs

# Cache for admin status to avoid repeated API calls
admin_cache = {}
CACHE_DURATION = timedelta(minutes=5)  # Cache admin status for 5 minutes


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
    # Skip if message is from owner
    if message.from_user and message.from_user.id == OWNER_ID:
        print(f"👑 Skipping media from owner (ID: {OWNER_ID})")
        return
    
    # Determine media type
    media_type = None
    if message.sticker:
        media_type = "sticker"
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
    elif message.animation:
        media_type = "animation"
    
    # Skip if not media
    if not media_type:
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
    
    # Determine delay based on media type
    if media_type == "sticker":
        base_delay = STICKER_DELAY
        # Add emoji to indicate sticker type
        sticker_info = ""
        if message.sticker.is_animated:
            sticker_info = " (animated)"
        elif message.sticker.is_video:
            sticker_info = " (video)"
        else:
            sticker_info = " (static)"
        
        print(f"🎨 Sticker{sticker_info} detected from @{sender} (ID: {sender_id}) in '{chat_title}'")
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
        delay_info = f"\n⏱️ Media delay: {DELAY}s | Sticker delay: {STICKER_DELAY}s"
        owner_info = f"\n👑 Owner ID: {OWNER_ID if OWNER_ID != 0 else 'Not set'}"
        
        await message.edit(f"Status in '{message.chat.title}': {status_text}{delay_info}{owner_info}")
    except Exception as e:
        await message.edit(f"❌ Error: {e}")
    
    await asyncio.sleep(5)
    await message.delete()


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


print("Starting media cleaner userbot...")
print(f"⏱️  Media deletion delay: {DELAY} seconds")
print(f"🎨 Sticker deletion delay: {STICKER_DELAY} seconds")
print(f"👑 Owner ID: {OWNER_ID if OWNER_ID != 0 else 'Not set'}")
print("Commands: clearcache, checkstatus, testdelete")
app.run()