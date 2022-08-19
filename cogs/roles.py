import discord
from discord.ext import commands
import logging


# TODO: Implement this to work with auto set items from initial startup.

class Roles(commands.Cog, name="Roles"):
    """Receives roles commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def agree(self, ctx: commands.Context):
        """for agreeing with the rules of the discord"""
        pass

    @commands.command()
    async def role(self, ctx: commands.Context):
        """use !role [role] to get the request role from roles"""
        pass

    @commands.command()
    async def roles(self, ctx: commands.Context):
        """Lists the roles you can request from the bot"""
        pass


def setup(bot: commands.Bot):
    bot.add_cog(Roles(bot))
