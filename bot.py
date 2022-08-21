#!/usr/bin/python3
import pickle
import discord
from discord.ext import commands
import os
import logging

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", case_insensitive=True, intents=intents)

# Remove Help command for custom one (for later)
# TODO: Implement custom help commands
# bot.remove_command("help")

bot_values_storage = {}


# Events
@bot.event
async def on_member_join(member):
    # TODO: Set this to apply a starting role so they can agree to rules (optional)
    guild = member.guild
    user = member
    role = discord.utils.get(member.guild.roles, name="")
    await user.add_roles(role)
    await guild.system_channel.send(f"Welcome to {guild.name}!")


@bot.event
async def on_member_remove(member):
    # Lets the Admins know who has left the server.
    # TODO: Set this up to work for set channel
    guild = member.guild
    user = member
    global bot_values_storage
    channel = member.guild.get_channel(bot_values_storage.get("leave"))
    await channel.send(f"{member.name}#{user.discriminator} - {member.display_name} has left the server")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That is not a command I know.")
    else:
        await ctx.send("Unable to complete the command.")
        logging.error(str(error))


@bot.command(name="setremove")
async def set_default_remove_channel(ctx):
    global bot_values_storage
    bot_values_storage["leave"] = ctx.message.channel.id  # TODO: Double check this
    save_bot_defaults()
    ctx.send(f"Notifications when someone leaves will be sent in this channel.")

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


def load_bot_defaults():
    """Loads any necessary default values for bot.py"""
    try:
        logging.info("Started loading bot values storage")
        global bot_values_storage
        with open('botValueStorage.pkl', 'rb') as file:
            bot_values_storage = pickle.load(file)
        logging.info("Finished loading bot values storage")
    except IOError as e:
        logging.error("Error on loading bot values storage: " + str(e))


def save_bot_defaults():
    """Saves any necessary default values for bot.py"""
    try:
        logging.info("Started pickling bot values storage")
        global bot_values_storage
        with open('botValueStorage.pkl', 'wb') as file:
            pickle.dump(bot_values_storage, file, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info("Finished pickling bot values storage")
    except IOError as e:
        logging.error("Error on saving trial count pickle: " + str(e))


@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name}")
    load_bot_defaults()
    await change_playing()  # Works in non-cog without self, requires self in cogs
    print("Bot is ready for use")


load_cogs()
if __name__ == '__main__':
    with open('Token.txt') as f:
        token = f.readline()
    bot.run(token)
