
import sys
import glob
import importlib
from pathlib import Path
import logging
import logging.config
import asyncio
from datetime import date, datetime

import pytz
from aiohttp import web
from pyrogram import idle, __version__
from pyrogram.raw.all import layer

from database.ia_filterdb import Media
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from lazybot import LazyPrincessBot
from lazybot.clients import initialize_clients
from util.keepalive import ping_server
from plugins import web_server


# ------------------------------
# Logging Setup
# ------------------------------
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)


# ------------------------------
# Plugin Loader
# ------------------------------
PLUGIN_PATH = "plugins/*.py"
plugin_files = glob.glob(PLUGIN_PATH)


# ------------------------------
# Main Async Bot Start
# ------------------------------
async def Lazy_start():

    print("\n========== INITIALIZING LAZY BOT ==========\n")

    # ⭐ Correct way to start Pyrogram client
    await LazyPrincessBot.start()

    # Basic bot info
    bot_info = await LazyPrincessBot.get_me()
    LazyPrincessBot.username = bot_info.username

    # Initialize multiple clients (if used)
    await initialize_clients()

    # -------------------------
    # Load Plugins Dynamically
    # -------------------------
    for file_name in plugin_files:
        path_obj = Path(file_name)
        plugin_name = path_obj.stem

        plugin_path = Path(f"plugins/{plugin_name}.py")
        import_path = f"plugins.{plugin_name}"

        spec = importlib.util.spec_from_file_location(import_path, plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[import_path] = module

        print(f"Lazy Imported => {plugin_name}")

    # Keep Alive on Heroku / Render
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    # Load Banned Users / Chats from DB
    banned_users, banned_chats = await db.get_banned()
    temp.BANNED_USERS = banned_users
    temp.BANNED_CHATS = banned_chats

    await Media.ensure_indexes()

    # Set temp data
    temp.ME = bot_info.id
    temp.U_NAME = bot_info.username
    temp.B_NAME = bot_info.first_name

    logging.info(f"{bot_info.first_name} | Pyrogram v{__version__} (Layer {layer}) started as @{bot_info.username}.")
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    # -------------------------
    # Restart Notification
    # -------------------------
    tz = pytz.timezone("Asia/Kolkata")
    today = date.today()
    now = datetime.now(tz)
    current_time = now.strftime("%H:%M:%S %p")

    # ⭐ FIX: Chat ID resolving now works
    await LazyPrincessBot.send_message(
        LOG_CHANNEL,
        script.RESTART_TXT.format(today, current_time)
    )

    # -------------------------
    # Start Web Server
    # -------------------------
    runner = web.AppRunner(await web_server())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # -------------------------
    # Idle (keep bot running)
    # -------------------------
    await idle()


# ------------------------------
# Main Entry
# ------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(Lazy_start())
    except KeyboardInterrupt:
        logging.info("Service Stopped Bye 👋")
