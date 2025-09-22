# Telegram Media Cleaner Bot

A modular Telegram userbot that automatically deletes media messages in groups with advanced configuration and user management.

## Features

- 🗑️ Automatic media deletion with configurable delays
- 👑 Owner and sudo user privileges
- ⏳ Temporary user exemptions
- ⚙️ Runtime configuration management
- 🎨 Separate delays for stickers/GIFs
- 📊 Rate limiting to prevent spam
- 💾 Persistent data storage
- 🔄 Pause/resume functionality

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd telegram-media-bot```

Commands
Configuration
.config - View current configuration
.setconfig <key> <value> - Update configuration
.resetconfig [confirm] - Reset to defaults

.setconfig delay 30
.setconfig stickerdelay 300
.setconfig maxdeletions 20 (minutes)
.setconfig owner 1234
.config

Admin
.checkstatus - Check bot status in current group
.clearcache - Clear admin rights cache
.testdelete - Test deletion (reply to a message)

Sudo Management
.addsudo - Add sudo user (reply or provide ID)
.rmsudo - Remove sudo user
.listsudo - List all sudo users

Exemptions
.exempt [duration] - Temporarily exempt user (e.g., .exempt 2h)
.listexempt - List active exemptions
.rmexempt - Remove user exemption

Media Control
.stickertoggle - Toggle sticker/GIF deletion
.stickerstatus - Check sticker deletion status
.clear [confirm] - Clear all media in current chat

Quick Actions
.pause [reason] - Pause bot
.resume - Resume bot