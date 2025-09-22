from pyrogram import Client
import asyncio

from config import Config, ConfigManager
from models import DataManager
from utils import RateLimiter, AdminCache
from handlers import (
    MediaHandler, 
    AdminHandler, 
    SudoHandler, 
    ExemptionHandler, 
    QuickActionsHandler
)

class MediaCleanerBot:
    """Main bot class that initializes and manages all components"""
    
    def __init__(self):
        # Initialize configuration
        self.config = Config()
        self.config_manager = ConfigManager(self.config)
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Initialize utilities
        self.rate_limiter = RateLimiter()
        self.admin_cache = AdminCache()
        
        # Initialize Pyrogram client
        self.client = self._create_client()
        
        # Initialize handlers
        self._initialize_handlers()
        
        # Store handlers in client for cross-reference
        self.client._custom_handlers = [
            self.media_handler,
            self.admin_handler,
            self.sudo_handler,
            self.exemption_handler,
            self.quick_actions_handler
        ]
    
    def _create_client(self) -> Client:
        """Create and configure Pyrogram client"""
        if self.config.SESSION_STRING:
            return Client(
                "media_cleaner",
                api_id=self.config.API_ID,
                api_hash=self.config.API_HASH,
                session_string=self.config.SESSION_STRING
            )
        else:
            return Client(
                "media_cleaner",
                api_id=self.config.API_ID,
                api_hash=self.config.API_HASH
            )
    
    def _initialize_handlers(self):
        """Initialize all command handlers"""
        # Initialize handlers with dependencies
        self.media_handler = MediaHandler(
            self.client,
            self.config_manager,
            self.data_manager,
            self.rate_limiter,
            self.admin_cache
        )
        
        self.admin_handler = AdminHandler(
            self.client,
            self.config_manager,
            self.admin_cache
        )
        # Add data reference for sudo count in status
        self.admin_handler.data = self.data_manager
        
        self.sudo_handler = SudoHandler(
            self.client,
            self.config_manager,
            self.data_manager
        )
        
        self.exemption_handler = ExemptionHandler(
            self.client,
            self.config_manager,
            self.data_manager
        )
        
        self.quick_actions_handler = QuickActionsHandler(self.client)
        # Set media handler reference for pause/resume
        self.quick_actions_handler.set_media_handler(self.media_handler)
    
    def print_startup_info(self):
        """Print startup information"""
        print("🚀 Starting Media Cleaner Userbot...")
        print(f"⏱️  Media deletion delay: {self.config_manager.delay} seconds")
        print(f"🎨 Sticker/GIF deletion delay: {self.config_manager.sticker_delay} seconds")
        print(f"👑 Owner ID: {self.config_manager.owner_id if self.config_manager.owner_id != 0 else 'Not set'}")
        print(f"🛡️ Loaded {len(self.data_manager.sudo_users)} sudo users")
        print(f"⏳ Loaded {len(self.data_manager.temp_exemptions)} active exemptions")
        print(f"🤖 Bot-only mode: {'ENABLED' if self.config_manager.is_bot_only_mode else 'DISABLED'}")
        print("\n📋 Available Commands:")
        print("Configuration: .config, .setconfig, .resetconfig")
        print("Admin: .checkstatus, .clearcache, .testdelete")
        print("Sudo: .addsudo, .rmsudo, .listsudo")
        print("Exemptions: .exempt, .listexempt, .rmexempt")
        print("Media: .stickertoggle, .stickerstatus, .clear")
        print("Quick Actions: .pause, .resume")
        print("\n✅ Bot initialized successfully!")
    
    def run(self):
        """Start the bot"""
        self.print_startup_info()
        self.client.run()

def main():
    """Main entry point"""
    bot = MediaCleanerBot()
    bot.run()

if __name__ == "__main__":
    main()
