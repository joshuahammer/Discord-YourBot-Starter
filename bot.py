#!/usr/bin/python3
import asyncio
import discord
from discord.ext import commands
import os
import logging
import yaml
import pymongo

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')  # , datefmt="%Y-%m-%d %H:%M:%S")

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="!", case_insensitive=True, intents=intents)


# Events
@bot.event
async def on_member_join(member):
    # TODO: Set this to apply a starting role so they can agree to rules (optional)
    guild = member.guild
    user = member
    role = discord.utils.get(member.guild.roles, name=bot.config['default'])
    await user.add_roles(role)
    await guild.system_channel.send(f"Welcome to {guild.name}!")


@bot.event
async def on_member_remove(member):
    # Lets the Admins know who has left the server.
    guild = member.guild
    user = member
    channel = guild.get_channel(bot.config['private'])
    await channel.send(f"{member.name}#{user.discriminator} - {member.display_name} has left the server")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That is not a command I know.")
    else:
        await ctx.send("Unable to complete the command.")
        logging.error(str(error))


def load_configurations():
    with open("config.yaml", 'r') as stream:
        data_loaded = yaml.safe_load(stream)
    return data_loaded


async def change_playing():
    await bot.change_presence(activity=discord.Game(name=bot.config['presence_message']))
    logging.info(f"Status has been set")


async def load_cogs():
    """Load cogs from the cogs folder"""
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logging.info(f"Successfully loaded {filename}")

            except Exception as e:
                logging.info(f"Failed to load {filename}")
                logging.error("cog load error: " + str(e))


@bot.event
async def on_ready():
    logging.info(f"Logged in as: {bot.user.name}")
    await change_playing()
    logging.info("Bot is ready for use")


async def main():
    async with bot:
        bot.config = load_configurations()
        await load_cogs()
        with open('Token.txt') as f:
            token = f.readline()
        await bot.start(token)


asyncio.run(main())
