#!/usr/bin/python3

import discord
from discord.ext import commands
import os
import logging

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", case_insensitive=True, intents=intents)

# Remove Help command for custom one (for later)
# TODO: Implement custom help commands
# bot.remove_command("help")


# Events
@bot.event
async def on_member_join(member):
    # TODO: Set this to apply a starting role so they can agree to rules (optional)
    guild = member.guild
    user = member
    role = discord.utils.get(member.guild.roles, name="")
    await user.add_roles(role)
    await guild.system_channel.send(f"Welcome to {guild.name}")


@bot.event
async def on_member_remove(member):
    # Lets the Admins know who has left the server.
    # TODO: Set this up to work for set channel
    guild = member.guild
    user = member
    channel = member.guild.get_channel(0)
    await channel.send(f"{member.name}#{user.discriminator} - {member.display_name} has left the server")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That is not a command I know.")
    else:
        await ctx.send("Unable to complete the command.")
        logging.error(str(error))


async def change_playing():
    await bot.change_presence(activity=discord.Game(name="Checking your bank accounts."))
    print(f"Status has been set")


def load_cogs():
    """Load cogs from the cogs folder"""
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Successfully loaded {filename}")

            except Exception as e:
                print(f"Failed to load {filename}")
                logging.error("cog load error: " + str(e))


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}")
    await change_playing()  # Works in non-cog without self, requires self in cogs
    print("Bot is ready for use")


load_cogs()
if __name__ == '__main__':
    with open('Token.txt') as f:
        token = f.readline()
    bot.run(token)
