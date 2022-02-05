import logging
import os

import discord
from discord.ext import commands

from mp2i.utils import database, resolver

# Create a logger for this file, __name__ will take the package name if this file
# will do not run as a scrip
logger = logging.getLogger(__name__)
TOKEN = os.getenv("DISCORD_TOKEN")


def run(token=None) -> None:
    """
    Runs the bot.
    token: Optional. You can pass your Discord token here or in a .env file
    """
    # Try to connect to the database or raise error
    database.test_connection()
    # Create a bot instance and activate all intents (more access to members infos)
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="<", intents=intents, self_bot=False)

    # loads all available cogs
    for cog in resolver.find_available_cogs():
        bot.load_extension(cog.__name__)

    bot.run(token or TOKEN)  # raise LoginFailure if the token is invalid
