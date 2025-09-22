import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

class QuickActionsHandler:
    """Handles quick action commands like pause/resume"""
    
    def __init__(self, client: Client, media_handler=None):
        self.client = client
        self.media_handler = media_handler  # Reference to MediaHandler for pause/resume
        
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all quick action handlers"""
        print("📌 Registering quick action handlers...")
        
        @self.client.on_message(filters.command("pause", prefixes=".") & filters.me)
        async def pause_bot_handler(client: Client, message: Message):
            await self.pause_bot(client, message)
        
        @self.client.on_message(filters.command("resume", prefixes=".") & filters.me)
        async def resume_bot_handler(client: Client, message: Message):
            await self.resume_bot(client, message)
        
        print("✅ Quick action handlers registered")
    
    def set_media_handler(self, media_handler):
        """Set reference to MediaHandler (called after initialization)"""
        self.media_handler = media_handler
    
    async def pause_bot(self, client: Client, message: Message):
        """Pause all deletion activities."""
        if not self.media_handler:
            await message.edit("❌ Bot not properly initialized!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        self.media_handler.bot_paused = True
        self.media_handler.pause_reason = " ".join(message.command[1:]) if len(message.command) > 1 else "Manual pause"
        
        await message.edit(f"⏸️ Bot paused. Reason: {self.media_handler.pause_reason}")
        print(f"⏸️ Bot paused. Reason: {self.media_handler.pause_reason}")
        
        await asyncio.sleep(3)
        await message.delete()
    
    async def resume_bot(self, client: Client, message: Message):
        """Resume deletion activities."""
        if not self.media_handler:
            await message.edit("❌ Bot not properly initialized!")
            await asyncio.sleep(3)
            await message.delete()
            return
        
        if not self.media_handler.bot_paused:
            await message.edit("⚠️ Bot is not paused!")
            await asyncio.sleep(2)
            await message.delete()
            return
        
        self.media_handler.bot_paused = False
        await message.edit("▶️ Bot resumed!")
        print(f"▶️ Bot resumed after pause. Previous reason: {self.media_handler.pause_reason}")
        self.media_handler.pause_reason = ""
        
        await asyncio.sleep(3)
        await message.delete()
