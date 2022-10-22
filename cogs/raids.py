import calendar
import datetime
import re
import discord
from discord.ext import commands
import pickle
import logging
import asyncio
from pytz import timezone
from enum import Enum
import pymongo

logging.basicConfig(level=logging.INFO)

class Role(Enum):
    DPS = "dps"
    HEALER = "healer"
    TANK = "tank"
    NONE = "none"


class Raid(commands.Cog, name="Raid"):
    """Class to hold trial information"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx: commands.Context):
        value = self.bot.config['administration']
        await ctx.send(value)


async def setup(bot):
    await bot.add_cog(Raid(bot))
