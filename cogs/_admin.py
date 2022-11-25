import discord
from discord.ext import commands
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')


class Admin(commands.Cog, name="Admin"):
    """Receives Administration commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
