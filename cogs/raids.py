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

logging.basicConfig(level=logging.INFO)

# Dictionary to store different trial info
storage = {}
trial_counter = {}
default_role = {}
prog_role_name = ""


class Role(Enum):
    DPS = "dps"
    HEALER = "healer"
    TANK = "tank"
    NONE = "none"


# TODO: Implement discord role limits (no cap on how many roles there can be)
#   vary that by associating them with numbers in a dictionary.

# TODO: Change raid count to include last day of raid.

# TODO: Change the code from ESO Trials to more generalized, all games.

# TODO: Change from specifically checking for Storm Bringers to a user-set admin role.

# TODO: Remove prog role stuff when completing role limits for rosters.


# Special class to store trial in'
class Raid:
    """Class to hold trial information"""

    def __init__(self, trial, date, leader, trial_dps={}, trial_healers={}, trial_tanks={}, backup_dps={},
                 backup_healers={}, backup_tanks={}):
        self.trial = trial
        self.date = date
        self.leader = leader
        self.trial_dps = trial_dps
        self.trial_healers = trial_healers
        self.trial_tanks = trial_tanks
        self.backup_dps = backup_dps
        self.backup_healers = backup_healers
        self.backup_tanks = backup_tanks

    def get_data(self):
        all_data = [self.trial, self.date, self.leader, self.trial_dps, self.trial_healers, self.trial_tanks,
                    self.backup_dps, self.backup_healers, self.backup_tanks]
        return all_data

    # Add people into the right spots
    def add_dps(self, n_dps, p_class="will be sadistic"):
        if len(self.trial_dps) < 8:
            self.trial_dps[n_dps] = p_class
        else:
            self.backup_dps[n_dps] = p_class

    def add_healer(self, n_healer, p_class="will be soft mommy dom"):
        if len(self.trial_healers) < 2:
            self.trial_healers[n_healer] = p_class
        else:
            self.backup_healers[n_healer] = p_class

    def add_tank(self, n_tank, p_class="will be masochistic"):
        if len(self.trial_tanks) < 2:
            self.trial_tanks[n_tank] = p_class
        else:
            self.backup_tanks[n_tank] = p_class

    def add_backup_dps(self, n_dps, p_class="could be sadistic"):
        self.backup_dps[n_dps] = p_class

    def add_backup_healer(self, n_healer, p_class="could be soft mommy dom"):
        self.backup_healers[n_healer] = p_class

    def add_backup_tank(self, n_tank, p_class="could be masochistic"):
        self.backup_tanks[n_tank] = p_class

    # remove people from right spots
    def remove_dps(self, n_dps):
        if n_dps in self.trial_dps:
            del self.trial_dps[n_dps]
        else:
            del self.backup_dps[n_dps]

    def remove_healer(self, n_healer):
        if n_healer in self.trial_healers:
            del self.trial_healers[n_healer]
        else:
            del self.backup_healers[n_healer]

    def remove_tank(self, n_tank):
        if n_tank in self.trial_tanks:
            del self.trial_tanks[n_tank]
        else:
            del self.backup_tanks[n_tank]

    # Fill the roster with backup people
    #   If there is less than max spots in main roster ,and more than 0 people in backup roster, then go ahead and move
    #   people from the backup roster to the primary roster until all slots are filled or backups are used up
    def fill_spots(self, num):
        try:
            loop = True
            while loop:
                if len(self.trial_dps) < 8 and len(self.backup_dps) > 0:
                    first = list(self.backup_dps.keys())[0]
                    self.trial_dps[first] = self.backup_dps.get(first)
                    del self.backup_dps[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.trial_healers) < 2 and len(self.backup_healers) > 0:
                    first = list(self.backup_healers.keys())[0]
                    self.trial_healers[first] = self.backup_healers.get(first)
                    del self.backup_healers[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.trial_tanks) < 2 and len(self.backup_tanks) > 0:
                    first = list(self.backup_tanks.keys())[0]
                    self.trial_tanks[first] = self.backup_tanks.get(first)
                    del self.backup_tanks[first]
                else:
                    loop = False
            save_to_doc()
            logging.info("Spots filled in trial id " + str(num))
        except Exception as e:
            logging.error("Fill_Spots error: " + str(e))


def save_trial_count():
    """Saves the dictionary that counts peoples trials in BOK"""
    try:
        logging.info("Started picking Trial Count")
        global trial_counter
        with open('trialCountStorage.pkl', 'wb') as file:
            pickle.dump(trial_counter, file, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info("Finished pickling Trial Count")
    except IOError as e:
        logging.error("Error on saving trial count pickle: " + str(e))


def load_trial_count():
    """Loads the dictionary that counts peoples trials in BOK"""
    try:
        logging.info("Started loading Trial Count")
        global trial_counter
        with open('trialCountStorage.pkl', 'rb') as file:
            trial_counter = pickle.load(file)
        logging.info("Finished loading Trial Count")
    except IOError as e:
        logging.error("Error on loading trial count pickle: " + str(e))


def save_prog_name():
    """Saves the prog role name to a pickle"""
    try:
        logging.info("Saving prog role name")
        global prog_role_name
        with open('progRoleName.pkl', 'wb') as file:
            pickle.dump(prog_role_name, file, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info("Finished pickling prog role name")
    except IOError as e:
        logging.error("Error on saving prog role name pickle: " + str(e))


def load_prog_name():
    """Loads the prog role name"""
    try:
        logging.info("Started loading prog role name")
        global prog_role_name
        with open('progRoleName.pkl', 'rb') as file:
            prog_role_name = pickle.load(file)
        logging.info("Finished loading prog role name")
    except IOError as e:
        logging.error("Error on loading prog role name pickle: " + str(e))


def save_to_doc():
    """Saves the trials to a pickle"""
    try:
        logging.info("Started pickling Trials")
        global storage
        db_file = open('trialStorage.pkl', 'wb')
        to_dump = []
        # get_data returns a list of the information in the trial, so the key and info is kep together in one list
        for key in storage:
            to_dump.append([key, storage[key].get_data()])
        pickle.dump(to_dump, db_file)
        db_file.close()
        logging.info("Finished pickling Trials")
    except Exception as e:
        logging.error("Error on saving trials pickle: " + str(e))


def load_trials():
    """Loads trials from the pickle"""
    try:
        global storage
        db_file = open('trialStorage.pkl', 'rb')
        all_data = pickle.load(db_file)
        for i in range(len(all_data)):
            # 0: trial, 1: date, 2: leader, 3: trial_dps = {},
            # 4: trial_healers = {}, 5: trial_tanks = {}, 6: backup_dps = {},
            # 7: backup_healers = {}, 8: backup_tanks = {}
            # It looks like this because the pickle file saves the object into a list, the list has to be unpacked
            #   back into the EsoTrial object, with another list inside it that must be unpacked into the object
            #   I dare not touch this again, lest I invoke the anger of the Gods.
            storage[all_data[i][0]] = Raid(all_data[i][1][0], all_data[i][1][1], all_data[i][1][2],
                                           all_data[i][1][3], all_data[i][1][4], all_data[i][1][5],
                                           all_data[i][1][6], all_data[i][1][7], all_data[i][1][8])
        db_file.close()
    except IOError as e:
        logging.error("Load Trials Error: " + str(e))


def save_default_roles():
    """Saves the default roles dictionary to a pickle"""
    try:
        logging.info("Started pickling Default Roles")
        global default_role
        with open('DefaultRolesStorage.pkl', 'wb') as file:
            pickle.dump(default_role, file, protocol=pickle.HIGHEST_PROTOCOL)
        logging.info("Finished pickling Default Roles")
    except IOError as e:
        logging.error("Error on saving default roles pickle: " + str(e))


def load_default_roles():
    """Loads the dictionary that holds peoples default roles"""
    try:
        logging.info("Started loading Default Roles pickle")
        global default_role
        with open('DefaultRolesStorage.pkl', 'rb') as file:
            default_role = pickle.load(file)
        logging.info("Finished loading Default Roles pickle")
    except IOError as e:
        logging.error("Error on loading Default Role pickle: " + str(e))


class Raids(commands.Cog, name="Raids"):
    """Receives trial commands"""

    def __init__(self, bot: commands.Bot):
        try:
            load_trials()
            load_trial_count()
            load_default_roles()
            load_prog_name()
            self.bot = bot
            logging.info("Loaded Raids and Raid Cog!")
        except Exception as e:
            logging.error("Error, unable to load:" + str(e))

    @commands.command()
    async def trial(self, ctx: commands.Context):
        """Creates a new trial and channel for BOK | format: !trial [leader],[trial],[date info]"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def suffix(d):
                    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

                msg = ctx.message.content
                msg = msg.split(" ", 1)  # Split into 2 parts of a list, the first space then the rest
                msg = msg[1]  # drop the !trial part
                leader, trial, date = msg.split(",")

                category = ctx.guild.get_channel(874077147084505099)
                new = re.sub('[^0-9]', '', date)  # Gotta get just the numbers for this part
                new = int(new)
                new_time = datetime.datetime.utcfromtimestamp(new)
                central = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz=timezone('US/Central'))
                weekday = calendar.day_name[central.weekday()]
                day = central.day
                new_name = trial + "-" + weekday + "-" + str(day) + suffix(day)
                channel = await category.create_text_channel(new_name)

                # create new trial and put it in storage for later use
                new_trial = Raid(trial, date, leader, trial_dps={}, trial_healers={},
                                 trial_tanks={}, backup_dps={}, backup_healers={}, backup_tanks={})
                storage[channel.id] = new_trial
                save_to_doc()
                logging.info("New Trial created: " + trial + " " + str(central))

                embed = discord.Embed(
                    title=trial + " " + date,
                    description="I hope people sign up for this.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Remember to spay or neuter your support!")
                embed.set_author(name="Raid Lead: " + leader)
                embed.add_field(name="Calling Healers!", value='To Heal Us!', inline=False)
                embed.add_field(name="Calling Tanks!", value='To Be Stronk!', inline=False)
                embed.add_field(name="Calling DPS!", value='To Stand In Stupid!', inline=False)
                await channel.send(embed=embed)
                await ctx.send("Channel and Roster created")
            else:
                await ctx.send("You do not have permission to do this.")
        except Exception as e:
            await ctx.send("Unable to complete the command.")
            logging.error("Trial creation error: " + str(e))

    @commands.command(name="prog")
    async def create_prog_channel(self, ctx: commands.Context):
        """Creates a new prog-role only channel | format: !trial [leader],[trial],[date info]"""
        try:
            global prog_role_name
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            prog_role = discord.utils.get(ctx.message.author.guild.roles, name=prog_role_name)
            bot_role = discord.utils.get(ctx.message.author.guild.roles, name="DrakApp")
            recruit_role = discord.utils.get(ctx.message.author.guild.roles, name="Recruits")
            founded_role = discord.utils.get(ctx.message.author.guild.roles, name="Kynes Founded")
            user = ctx.message.author
            if user in role.members:
                def suffix(d):
                    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

                msg = ctx.message.content
                msg = msg.split(" ", 1)  # Split into 2 parts of a list, the first space then the rest
                msg = msg[1]  # drop the !trial part
                leader, trial, date = msg.split(",")

                category = ctx.guild.get_channel(874077147084505099)
                new = re.sub('[^0-9]', '', date)  # Gotta get just the numbers for this part
                new = int(new)
                new_time = datetime.datetime.utcfromtimestamp(new)
                central = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz=timezone('US/Central'))
                weekday = calendar.day_name[central.weekday()]
                day = central.day
                new_name = f"prog-{weekday}-{str(day)}{str(suffix(day))}"
                channel = await category.create_text_channel(new_name)
                await channel.set_permissions(bot_role, view_channel=True)
                await channel.set_permissions(recruit_role, view_channel=False)
                await channel.set_permissions(founded_role, view_channel=False)
                await channel.set_permissions(prog_role, view_channel=True)
                await channel.set_permissions(role, view_channel=True)

                # create new trial and put it in storage for later use
                new_trial = Raid(trial, date, leader, trial_dps={}, trial_healers={},
                                 trial_tanks={}, backup_dps={}, backup_healers={}, backup_tanks={})
                storage[channel.id] = new_trial
                save_to_doc()
                logging.info("New Trial created: " + trial + " " + str(central))

                embed = discord.Embed(
                    title=trial + " " + date,
                    description="I hope people sign up for this.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Remember to spay or neuter your support!")
                embed.set_author(name="Raid Lead: " + leader)
                embed.add_field(name="Calling Healers!", value='To Heal Us!', inline=False)
                embed.add_field(name="Calling Tanks!", value='To Be Stronk!', inline=False)
                embed.add_field(name="Calling DPS!", value='To Stand In Stupid!', inline=False)
                await channel.send(embed=embed)
                await ctx.send("Channel and Roster created")
            else:
                await ctx.send("You do not have permission to do this.")
        except Exception as e:
            await ctx.send("Unable to complete the command.")
            logging.error("Trial creation error: " + str(e))

    @commands.command()
    async def su(self, ctx: commands.Context):
        """Use !su [optional role] and/or [optional message]. Remember to set your default!"""
        try:
            msg = ctx.message.content
            global storage
            global default_role
            single = False  # A variable to check if someone just used !su
            worked = False
            swapped = False
            slotted = Role.NONE
            msg_change = False
            og_msg = ""
            msg = msg.split(" ", 2)
            if len(msg) == 1:
                single = True
            channel = ctx.message.channel.id
            user_id = ctx.message.author.id
            trial = storage.get(channel)
            if user_id in trial.trial_dps.keys():
                og_msg = trial.trial_dps.get(user_id)
                slotted = Role.DPS
                trial.remove_dps(user_id)
                swapped = True

            elif user_id in trial.backup_dps.keys():
                og_msg = trial.backup_dps.get(user_id)
                trial.remove_dps(user_id)
                slotted = Role.DPS
                swapped = True

            elif user_id in trial.trial_healers.keys():
                og_msg = trial.trial_healers.get(user_id)
                trial.remove_healer(user_id)
                slotted = Role.HEALER
                swapped = True

            elif user_id in trial.backup_healers.keys():
                og_msg = trial.backup_healers.get(user_id)
                trial.remove_healer(user_id)
                slotted = Role.HEALER
                swapped = True

            elif user_id in trial.trial_tanks.keys():
                og_msg = trial.trial_tanks.get(user_id)
                trial.remove_tank(user_id)
                slotted = Role.TANK
                swapped = True

            elif user_id in trial.backup_tanks.keys():
                og_msg = trial.backup_tanks.get(user_id)
                trial.remove_tank(user_id)
                slotted = Role.TANK
                swapped = True

            # Just along check to verify it is not any of the defaults or empty first dps then healer then tank
            if slotted != Role.NONE and og_msg != "" and og_msg != "could be sadistic" and og_msg != "will be sadistic" \
                    and og_msg != "will be soft mommy dom" and og_msg != "could be soft mommy dom" \
                    and og_msg != "will be masochistic" and og_msg != "could be masochistic":
                msg_change = True
                # Now that we have determined that the original message is not default, need to adjust accordingly
                #   in non-role change situations. IE: just calling !su or !bu to swap which roster they are on

            if not single:
                role = msg[1].lower()
                if role == "dps" or role == "healer" or role == "tank":
                    # Check if there is an optional message or not
                    if len(msg) == 3:
                        # The message has a SU, a Role, and a message. Now to grab the right role
                        if role == "dps":
                            trial.add_dps(user_id, msg[2])
                            worked = True
                        elif role == "healer":
                            trial.add_healer(user_id, msg[2])
                            worked = True
                        elif role == "tank":
                            trial.add_tank(user_id, msg[2])
                            worked = True
                    else:
                        # The message has a SU and a Role
                        if role == "dps":
                            if slotted == Role.DPS and msg_change:
                                trial.add_dps(user_id, og_msg)
                            else:
                                trial.add_dps(user_id)
                            worked = True
                        elif role == "healer":
                            if slotted == Role.HEALER and msg_change:
                                trial.add_healer(user_id, og_msg)
                            else:
                                trial.add_healer(user_id)
                            worked = True
                        elif role == "tank":
                            if slotted == Role.TANK and msg_change:
                                trial.add_tank(user_id, og_msg)
                            else:
                                trial.add_tank(user_id)
                            worked = True
                else:
                    # No role, need to grab default
                    if len(msg) == 3:
                        msg = msg[1] + " " + msg[2]  # merge together the message if needed
                    else:
                        msg = msg[1]
                    role = default_role.get(user_id)
                    if role == "dps":
                        trial.add_dps(user_id, msg)
                        worked = True
                    elif role == "healer":
                        trial.add_healer(user_id, msg)
                        worked = True
                    elif role == "tank":
                        trial.add_tank(user_id, msg)
                        worked = True
            else:
                # User just called !su, no message, no role
                role = default_role.get(user_id)
                if role == "dps":
                    if slotted == Role.DPS and msg_change:
                        trial.add_dps(user_id, og_msg)
                    else:
                        trial.add_dps(user_id)
                    worked = True
                elif role == "healer":
                    if slotted == Role.HEALER and msg_change:
                        trial.add_healer(user_id, og_msg)
                    else:
                        trial.add_healer(user_id)
                    worked = True
                elif role == "tank":
                    if slotted == Role.TANK and msg_change:
                        trial.add_tank(user_id, og_msg)
                    else:
                        trial.add_tank(user_id)
                    worked = True
            if worked:
                # Check if the user is already in one of the rosters
                storage[channel] = trial
                save_to_doc()
                if swapped:
                    await ctx.reply("Swapped!")
                else:
                    await ctx.reply("Added!")
            else:
                await ctx.reply("Unable to sign up. Remember to check <#932438565009379358> if you are stuck!")
        except Exception as e:
            await ctx.send("Unable to sign up.")
            logging.error("SU error:" + str(e))

    @commands.command()
    async def bu(self, ctx: commands.Context):
        """Use !bu [optional role] and/or [optional message]. Remember to set your default!"""
        try:
            msg = ctx.message.content
            global storage
            global default_role
            single = False  # A variable to check if someone just used !bu
            worked = False
            swapped = False
            slotted = Role.NONE
            msg_change = False
            og_msg = ""
            msg = msg.split(" ", 2)
            if len(msg) == 1:
                single = True
            channel = ctx.message.channel.id
            user_id = ctx.message.author.id
            trial = storage.get(channel)
            # Check if the user is already in one of the rosters
            if user_id in trial.trial_dps.keys():
                og_msg = trial.trial_dps.get(user_id)
                slotted = Role.DPS
                trial.remove_dps(user_id)
                swapped = True

            elif user_id in trial.backup_dps.keys():
                og_msg = trial.backup_dps.get(user_id)
                trial.remove_dps(user_id)
                slotted = Role.DPS
                swapped = True

            elif user_id in trial.trial_healers.keys():
                og_msg = trial.trial_healers.get(user_id)
                trial.remove_healer(user_id)
                slotted = Role.HEALER
                swapped = True

            elif user_id in trial.backup_healers.keys():
                og_msg = trial.backup_healers.get(user_id)
                trial.remove_healer(user_id)
                slotted = Role.HEALER
                swapped = True

            elif user_id in trial.trial_tanks.keys():
                og_msg = trial.trial_tanks.get(user_id)
                trial.remove_tank(user_id)
                slotted = Role.TANK
                swapped = True

            elif user_id in trial.backup_tanks.keys():
                og_msg = trial.backup_tanks.get(user_id)
                trial.remove_tank(user_id)
                slotted = Role.TANK
                swapped = True

            # Just a long check to verify it is not any of the defaults or empty first dps then healer then tank
            if slotted != Role.NONE and og_msg != "" and og_msg != "could be sadistic" and og_msg != "will be sadistic" \
                    and og_msg != "will be soft mommy dom" and og_msg != "could be soft mommy dom" \
                    and og_msg != "will be masochistic" and og_msg != "could be masochistic":
                msg_change = True
                # Now that we have determined that the original message is not default, need to adjust accordingly
                #   in non-role change situations. IE: just calling !su or !bu to swap which roster they are on

            if not single:
                role = msg[1].lower()
                if role == "dps" or role == "healer" or role == "tank":
                    # Check if there is an optional message or not
                    if len(msg) == 3:
                        # The message has a SU, a Role, and a message. Now to grab the right role
                        if role == "dps":
                            trial.add_backup_dps(user_id, msg[2])
                            worked = True
                        elif role == "healer":
                            trial.add_backup_healer(user_id, msg[2])
                            worked = True
                        elif role == "tank":
                            trial.add_backup_tank(user_id, msg[2])
                            worked = True
                    else:
                        # The message has a SU and a Role
                        if role == "dps":
                            if slotted == Role.DPS and msg_change:
                                trial.add_backup_dps(user_id, og_msg)
                            else:
                                trial.add_backup_dps(user_id)
                            worked = True
                        elif role == "healer":
                            if slotted == Role.HEALER and msg_change:
                                trial.add_backup_healer(user_id, og_msg)
                            else:
                                trial.add_backup_healer(user_id)
                            worked = True
                        elif role == "tank":
                            if slotted == Role.TANK and msg_change:
                                trial.add_backup_tank(user_id, og_msg)
                            else:
                                trial.add_backup_tank(user_id)
                            worked = True
                else:
                    # No role, need to grab default
                    if len(msg) == 3:
                        msg = msg[1] + " " + msg[2]  # merge together the message if needed
                    else:
                        msg = msg[1]
                    role = default_role.get(user_id)
                    if role == "dps":
                        trial.add_backup_dps(user_id, msg)
                        worked = True
                    elif role == "healer":
                        trial.add_backup_healer(user_id, msg)
                        worked = True
                    elif role == "tank":
                        trial.add_backup_tank(user_id, msg)
                        worked = True
            else:
                # User just called !su, no message, no role
                role = default_role.get(user_id)
                if role == "dps":
                    if slotted == Role.DPS and msg_change:
                        trial.add_backup_dps(user_id, og_msg)
                    else:
                        trial.add_backup_dps(user_id)
                    worked = True
                elif role == "healer":
                    if slotted == Role.HEALER and msg_change:
                        trial.add_backup_healer(user_id, og_msg)
                    else:
                        trial.add_backup_healer(user_id)
                    worked = True
                elif role == "tank":
                    if slotted == Role.TANK and msg_change:
                        trial.add_backup_tank(user_id, og_msg)
                    else:
                        trial.add_backup_tank(user_id)
                    worked = True
            if worked:
                storage[channel] = trial
                save_to_doc()
                if swapped:
                    await ctx.reply("Swapped!")
                else:
                    await ctx.reply("Added for backup!")
            else:
                await ctx.reply("Unable to sign up as backup. Remember to check <#932438565009379358> if you are stuck!"
                                )
        except Exception as e:
            await ctx.send("Unable to sign up as backup")
            logging.error("BU error:" + str(e))

    @commands.command()
    async def wd(self, ctx: commands.Context):
        """Use !wd to remove yourself from the roster. This will remove you from both BU and Main rosters"""
        try:
            worked = False
            num = ctx.message.channel.id
            trial = storage.get(num)
            user_id = ctx.message.author.id
            if user_id in trial.trial_dps.keys() or \
                    user_id in trial.backup_dps.keys():
                trial.remove_dps(user_id)
                worked = True

            elif user_id in trial.trial_healers.keys() or \
                    user_id in trial.backup_healers.keys():
                trial.remove_healer(user_id)
                worked = True

            elif user_id in trial.trial_tanks.keys() or \
                    user_id in trial.backup_tanks.keys():
                trial.remove_tank(user_id)
                worked = True
            else:
                if not worked:
                    await ctx.send("You are not signed up for this Trial")
            if worked:
                for i in ctx.guild.members:
                    if i.id == user_id:
                        await ctx.reply("Removed :(")
                storage[num] = trial
                save_to_doc()
        except Exception as e:
            await ctx.send("Unable to withdraw you from the roster")
            logging.error("WD error: " + str(e))

    @commands.command()
    async def fill(self, ctx: commands.Context):
        """For trial leaders to fill the roster from the backup roster"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to have the roster closed and "
                                        "the channel deleted")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, fill has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    channel = ctx.guild.get_channel(num)
                                    trial = storage.get(num)
                                    await ctx.send("Fill Trial: " + trial.trial + " - " + channel.name + " (y/n)?")
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=15.0)
                                    confirm = confirm.content.lower()
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, fill has timed out")
                                    return
                                else:
                                    # Verify that the trial did happen, and if so then add a +1 to each person's count
                                    if confirm == "y":
                                        trial.fill_spots(num)
                                        storage[num] = trial
                                        save_to_doc()
                                        await ctx.send("Spots filled!")
                                        run = False
                                    else:
                                        if confirm == 'n':
                                            await ctx.send("Returning to menu.")
                                        else:
                                            await ctx.send("Invalid response, returning to menu.")
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Fill error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command()
    async def status(self, ctx: commands.Context):
        """Prints out a list of all who are signed up as main and backups"""
        try:
            num = ctx.message.channel.id
            primary_embed = await self.print_roster(num, ctx.guild.id)

            await ctx.send(embed=primary_embed)
        except Exception as e:
            logging.error("Status check error: " + str(e))
            await ctx.send("Unable to send status.")

    @commands.command()
    async def msg(self, ctx: commands.Context):
        """!msg [message] to modify your message in the embed"""
        trial = storage.get(ctx.message.channel.id)
        found = True
        msg = ctx.message.content
        msg = msg.split(" ", 1)
        msg = msg[1]
        user_id = ctx.message.author.id
        if user_id in trial.trial_dps.keys():
            trial.trial_dps[user_id] = msg
        elif user_id in trial.backup_dps:
            trial.backup_dps[user_id] = msg
        elif user_id in trial.trial_healers:
            trial.trial_healers[user_id] = msg
        elif user_id in trial.backup_healers:
            trial.backup_healers[user_id] = msg
        elif user_id in trial.trial_tanks:
            trial.trial_tanks[user_id] = msg
        elif user_id in trial.backup_tanks:
            trial.backup_tanks[user_id] = msg
        else:
            await ctx.send("You are not signed up for the trial.")
            found = False
        if found:
            await ctx.send("Updated!")

    @commands.command(name="call")
    async def send_message_to_everyone(self, ctx: commands.Context):
        """For Raid Leads. A way to send a ping to everyone in a roster."""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author
                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to gather or ping everyone")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, call has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    await ctx.send("Enter the message to send, or cancel to exit.")
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=30.0)
                                    msg = confirm.content
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, call has timed out")
                                    return
                                else:
                                    if msg.lower() == "cancel":
                                        await ctx.send("Exiting command")
                                        return
                                    else:
                                        confirmation_message = f"Send this message:\n{msg}\n\ny/n?"
                                        await ctx.send(confirmation_message)
                                        confirm = await self.bot.wait_for(event="message", check=check, timeout=15.0)
                                        confirm = confirm.content
                                        if confirm.lower() == "y":
                                            await self.call_everyone(num, ctx, msg)
                                            run = False
                                            await ctx.send("Message sent.")
                                        elif confirm.lower() == "n":
                                            await ctx.send("Returning to start of section.")
                                        else:
                                            await ctx.send("Not a valid input, returning to start of section.")

                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Call error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command()
    async def save(self, ctx: commands.Context):
        """For Officers: Saves roster data to storage"""
        if ctx.message.author.id == 212634819190849536:
            try:
                save_to_doc()
                await ctx.send("Saved!")
            except Exception as e:
                await ctx.send("Issue saving.")
                print("Error when saving data: " + str(e))
        else:
            await ctx.send("You do not have permission to do that.")

    @commands.command()
    async def load(self, ctx: commands.Context):
        """For Officers: Loads the trials from storage into the bot"""
        if ctx.message.author.id == 212634819190849536:
            try:
                global storage
                db_file = open('trialStorage.pkl', 'rb')
                all_data = pickle.load(db_file)
                for i in range(len(all_data)):
                    # 0: trial, 1: timestamp, 2: leader, 3: trial_dps = {},
                    # 4: trial_healers = {}, 5: trial_tanks = {}, 6: backup_dps = {},
                    # 7: backup_healers = {}, 8: backup_tanks = {}
                    storage[all_data[i][0]] = Raid(all_data[i][1][0], all_data[i][1][1], all_data[i][1][2],
                                                   all_data[i][1][3],
                                                   all_data[i][1][4], all_data[i][1][5], all_data[i][1][6],
                                                   all_data[i][1][7], all_data[i][1][8])

                db_file.close()
                await ctx.send("Loaded!")
            except Exception as e:
                await ctx.send("Data not loaded. Have Drak check code.")
                logging.error("Load error: " + str(e))
        else:
            await ctx.send("You do not have permission to do that.")

    # Commands for adding, removing, and modifying the roster

    @commands.command()
    async def remove(self, ctx: commands.Context):
        """For Officers: Removes someone from the roster"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to select the roster")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, remove has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    trial = storage.get(num)
                                    roster = []
                                    counter = 1
                                    total = ""
                                    # Print out everyone and put them in a list to get from
                                    for i in trial.trial_dps.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i).display_name}\n"
                                        counter += 1
                                    for i in trial.trial_healers.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i)}\n"
                                        counter += 1
                                    for i in trial.trial_tanks.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i)}\n"
                                        counter += 1
                                    for i in trial.backup_dps.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i)}\n"
                                        counter += 1
                                    for i in trial.backup_healers.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i)}\n"
                                        counter += 1
                                    for i in trial.backup_tanks.keys():
                                        roster.append(i)
                                        total += f"{counter}: {ctx.guild.get_member(i)}\n"
                                        counter += 1
                                    await ctx.send(total)
                                    await ctx.send("Enter the number of who you want to remove.")
                                    choice = await self.bot.wait_for(event="message", check=check, timeout=30.0)
                                    choice = int(choice.content)
                                    choice -= 1
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, remove has timed out")
                                    return
                                else:
                                    try:
                                        person = roster[choice]
                                        await ctx.send(f"Remove: {ctx.guild.get_member(person).display_name} (y/n)?")
                                        confirm = await self.bot.wait_for(event="message", check=check, timeout=15.0)
                                        confirm = confirm.content.lower()
                                    except asyncio.TimeoutError:
                                        await ctx.send(f"{ctx.author.mention}, remove has timed out")
                                        return
                                    else:
                                        if confirm == "y":
                                            worked = True
                                            found = False
                                            if person in trial.trial_dps.keys() or person in trial.backup_dps.keys():
                                                trial.remove_dps(person)
                                                found = True
                                            if person in trial.trial_healers.keys() or \
                                                    person in trial.backup_healers.keys() and not found:
                                                trial.remove_healer(person)
                                                found = True
                                            if person in trial.trial_tanks.keys() or \
                                                    person in trial.backup_tanks.keys() and not found:
                                                trial.remove_tank(person)
                                            else:
                                                if not found:
                                                    worked = False
                                                    await ctx.send("Person not found.")
                                            if worked:
                                                await ctx.send(f"Removed "
                                                               f"{ctx.channel.guild.get_member(person).display_name}")
                                                storage[num] = trial
                                                save_to_doc()
                                            run = False
                                        else:
                                            if confirm == 'n':
                                                await ctx.send("Returning to menu.")
                                            else:
                                                await ctx.send("Invalid response, returning to menu.")
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Remove error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command()
    async def add(self, ctx: commands.Context, p_type, member: discord.Member):
        """Officer command to manually add someone to a roster"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")  # check if user has perms
            user = ctx.message.author
            if user in role.members:
                num = ctx.message.channel.id  # Get channel id, use it to grab trial, and add user into the trial
                trial = storage.get(num)
                added_member_id = member.id
                worked = False
                if p_type.lower() == "dps":
                    trial.add_dps(added_member_id)
                    worked = True
                elif p_type.lower() == "healer":
                    trial.add_healer(added_member_id)
                    worked = True
                elif p_type.lower() == "tank":
                    trial.add_tank(added_member_id)
                    worked = True
                else:
                    await ctx.send("could not find role")
                if worked:  # If True
                    storage[num] = trial  # save trial and save back to storage
                    save_to_doc()
                    await ctx.send("Player added!")
            else:
                await ctx.send("You do not have permission to do that.")
        except Exception as e:
            await ctx.send("Something has gone wrong.")
            logging.error("Add user error: " + str(e))

    @commands.command()
    async def leader(self, ctx: commands.Context):
        """For Officers: Replaces the leader of a trial"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to have the leader changed")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, leader replace has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    trial = storage.get(num)
                                    await ctx.send("Enter the new leader for Trial: " + trial.trial)
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=30.0)
                                    leader = confirm.content
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, leader replace has timed out")
                                    return
                                else:
                                    old_leader = trial.leader
                                    trial.leader = leader
                                    storage[num] = trial
                                    save_to_doc()
                                    await ctx.send(
                                        "Trial leader has been changed from " + old_leader + " to " + trial.leader)
                                    run = False
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Leader change error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="changetrial")
    async def change_trial(self, ctx: commands.Context):
        """For Officers: Replaces the trial of a trial"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                def suffix(d):
                    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to have the trial changed")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, trial change has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    channel = ctx.guild.get_channel(num)
                                    trial = storage.get(num)
                                    await ctx.send("Enter the new Trial: " + trial.trial)
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=30.0)
                                    new_trial = confirm.content
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, trial change has timed out")
                                    return
                                else:
                                    old_trial = trial.trial
                                    trial.trial = new_trial
                                    storage[num] = trial
                                    save_to_doc()
                                    await ctx.send("Trial has been changed from " + old_trial + " to " + trial.trial)
                                    new = re.sub('[^0-9]', '', trial.date)  # Gotta get just the numbers for this part
                                    new = int(new)
                                    time = datetime.datetime.utcfromtimestamp(new)
                                    central = time.replace(tzinfo=datetime.timezone.utc).astimezone(tz=timezone('US/Central'))
                                    weekday = calendar.day_name[central.weekday()]
                                    day = central.day
                                    new_name = trial.trial + "-" + weekday + "-" + str(day) + suffix(day)
                                    await channel.edit(name=new_name)
                                    run = False
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Change Trial change error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="datetime")
    async def change_date_time(self, ctx: commands.Context):
        """For Officers: Replaces the date of a trial"""

        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                def suffix(d):
                    return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to have the trial date changed")
                        await ctx.send(total)
                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, date change has timed out")
                        return
                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    channel = ctx.guild.get_channel(num)
                                    trial = storage.get(num)
                                    await ctx.send("Enter the new date for Trial: " + trial.trial)
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=30.0)
                                    new_date = confirm.content
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, date change has timed out")
                                    return
                                else:
                                    # Verify that the trial did happen, and if so then add a +1 to each person's count
                                    old_date = trial.date
                                    trial.date = new_date
                                    storage[num] = trial
                                    save_to_doc()
                                    await ctx.send("Trial has been changed from " + old_date + " to " + trial.date)

                                    new = re.sub('[^0-9]', '', new_date)
                                    new = int(new)
                                    new_time = datetime.datetime.utcfromtimestamp(new)
                                    central = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz=timezone('US/Central'))
                                    weekday = calendar.day_name[central.weekday()]
                                    day = central.day
                                    new_name = trial.trial + "-" + weekday + "-" + str(day) + suffix(day)
                                    await channel.edit(name=new_name)
                                    run = False
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Change Trial change error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    async def print_roster(self, num, guild_id):
        try:
            global storage
            trial = storage.get(num)
            dps_count = 0
            healer_count = 0
            tank_count = 0
            guild = self.bot.get_guild(guild_id)
            names = ""
            embed = discord.Embed(
                title=trial.trial + " " + trial.date,
                color=discord.Color.green()
            )
            embed.set_footer(text="Remember to spay or neuter your support!")
            embed.set_author(name="Raid Lead: " + trial.leader)

            # HEALERS
            if not len(trial.trial_healers) == 0:
                to_remove = []
                for i in trial.trial_healers:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        # Check if there are no healers left, if so then set names to None
                        if len(to_remove) == len(trial.trial_healers):
                            names = "None"
                    else:
                        names += "<:Healer:933835785352904864>" + member_name.display_name + " " + \
                                 trial.trial_healers[i] + " " + "\r\n"
                        healer_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_healer(i)
                    save_to_doc()

            # TANKS
            if not len(trial.trial_tanks) == 0:
                to_remove = []
                tanks = trial.trial_tanks
                for i in tanks:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(trial.trial_tanks):
                            names = "None"
                    else:
                        names += "<:Tank:933835838951948339>" + member_name.display_name + " " + trial.trial_tanks[i] \
                                 + " " + "\r\n"
                        tank_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_tank(i)
                    save_to_doc()
            # DPS
            if not len(trial.trial_dps) == 0:
                to_remove = []
                dps = trial.trial_dps
                for i in dps:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(trial.trial_dps):
                            names = "None"
                    else:
                        names += "<:DPS:933835811684757514>" + member_name.display_name + " " \
                                 + trial.trial_dps[i] + " " + "\r\n"
                        dps_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_dps(i)
                    save_to_doc()

            if not names == "":
                embed.add_field(name="Roster", value=names, inline=False)

                names = "Healers: " + str(healer_count) + " \nTanks: " + str(tank_count) + " \nDPS: " + str(dps_count)
                embed.add_field(name="Total", value=names, inline=False)

            names = ""

            # Show Backup/Overflow Roster
            dps_count = 0
            healer_count = 0
            tank_count = 0
            # BACKUP HEALERS
            if not len(trial.backup_healers) == 0:
                to_remove = []
                backup_healers = trial.backup_healers
                for i in backup_healers:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(trial.backup_healers):
                            names = "None"
                    else:
                        names += "<:Healer:933835785352904864>" + member_name.display_name + " " + \
                                 trial.backup_healers[i] + "\r\n"
                        healer_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_healer(i)
                    save_to_doc()

            # BACKUP TANKS
            if not len(trial.backup_tanks) == 0:
                to_remove = []
                tanks = trial.backup_tanks
                for i in tanks:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(trial.backup_tanks):
                            names = "None"
                    else:
                        names += "<:Tank:933835838951948339>" + member_name.display_name + " " + trial.backup_tanks[i] \
                                 + "\r\n"
                        tank_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_tank(i)
                    save_to_doc()
            # BACKUP DPS
            if not len(trial.backup_dps) == 0:
                to_remove = []
                dps = trial.backup_dps
                for i in dps:
                    member_name = guild.get_member(i)
                    if member_name is None:
                        to_remove.append(i)
                        if len(to_remove) == len(trial.backup_dps):
                            names = "None"
                    else:
                        names += "<:DPS:933835811684757514>" + member_name.display_name + " " + trial.backup_dps[i] \
                                 + "\r\n"
                        dps_count += 1
                if len(to_remove) > 0:
                    for i in to_remove:
                        trial.remove_dps(i)
                    save_to_doc()

            if not names == "":
                embed.add_field(name="Backups", value=names, inline=False)

                names = "Healers: " + str(healer_count) + "\nTanks: " + str(tank_count) + "\nDPS: " + str(dps_count)
                embed.add_field(name="Total Backups", value=names, inline=False)

            return embed
        except Exception as e:
            logging.error("Print roster error: " + str(e))

    async def call_everyone(self, num, ctx, msg):
        try:
            trial = storage.get(num)
            names = "\nHealers \n"
            for i in trial.trial_healers:
                for j in ctx.guild.members:
                    if i == j.id:
                        names += j.mention + "\n"
            if len(trial.trial_healers) == 0:
                names += "None " + "\n"

            names += "\nTanks \n"
            for i in trial.trial_tanks:
                for j in ctx.guild.members:
                    if i == j.id:
                        names += j.mention + "\n"
            if len(trial.trial_tanks) == 0:
                names += "None" + "\n"

            names += "\nDPS \n"
            for i in trial.trial_dps:
                for j in ctx.guild.members:
                    if i == j.id:
                        names += j.mention + "\n"
            if len(trial.trial_dps) == 0:
                names += "None" + "\n"

            channel = ctx.guild.get_channel(num)
            await channel.send(f"A MESSAGE FOR:\n{names}\n{msg}")
        except Exception as e:
            await ctx.send("Error printing roster")
            logging.error("Summon error: " + str(e))

    @commands.command()
    async def close(self, ctx: commands.Context):
        """Closes a roster and deletes a channel for a trial"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                def check(m: discord.Message):  # m = discord.Message.
                    return user == m.author

                #  checking author and channel, you could add a line to check the content.
                # and m.content == "xxx"
                # the check won't become True until it detects (in the example case): xxx
                # but that's not what we want here.

                # Not using this but keeping it in comments for later development
                run = True
                while run:
                    try:
                        counter = 1
                        total = ""
                        key_list = []
                        for i in storage.keys():
                            channel = ctx.guild.get_channel(i)
                            if channel is not None:
                                total += str(counter) + ": " + channel.name + "\n"
                            else:
                                total += str(counter) + ": " + str(i) + "\n"
                            counter += 1
                            key_list.append(i)
                        total += "0: Exit \n"
                        await ctx.reply("Enter a number from the list below to have the roster closed and "
                                        "the channel deleted")
                        await ctx.send(total)

                        #                        event = on_message without on_
                        msg = await self.bot.wait_for(event='message', check=check, timeout=15.0)
                        # msg = discord.Message
                    except asyncio.TimeoutError:
                        # at this point, the check didn't become True, let's handle it.
                        await ctx.send(f"{ctx.author.mention}, close has timed out")
                        return

                    else:
                        # at this point the check has become True and the wait_for has done its work now we can do ours
                        # we could also do things based on the message content here, like so
                        # if msg.content == "this is cool":
                        #    return await ctx.send("wait_for is indeed a cool method")

                        try:
                            # Since the bot uses python 3.10, dictionaries are indexed by the order of insertion.
                            #   However, I already wrote it like this. Oh well.
                            choice = int(msg.content)
                            choice -= 1  # Need to lower it by one for the right number to get
                            if choice == -1:
                                await ctx.send("Exiting command")
                                return
                            try:
                                num = key_list[choice]
                                try:
                                    channel = ctx.guild.get_channel(num)
                                    trial = storage.get(num)
                                    # Arma is likely to delete the channel but not the trial, best to account for that
                                    if channel is None:
                                        await ctx.send("Delete trial: " + trial.trial + " - " + str(num) + " (y/n)?")
                                    else:
                                        await ctx.send("Delete trial and channel: " + trial.trial + " - " + channel.name
                                                       + " (y/n)?")
                                    confirm = await self.bot.wait_for(event="message", check=check, timeout=15.0)
                                    confirm = confirm.content.lower()
                                except asyncio.TimeoutError:
                                    await ctx.send(f"{ctx.author.mention}, close has timed out")
                                    return
                                else:
                                    # Verify that the trial did happen, and if so then add a +1 to each person's count
                                    if confirm == "y":
                                        if num in storage.keys():
                                            try:
                                                await ctx.send("Increase everyone's Trial Count (y/n)?")
                                                confirm = await self.bot.wait_for(event="message", check=check,
                                                                                  timeout=15.0)
                                                confirm = confirm.content.lower()

                                                if confirm == "y":
                                                    trial = storage.get(num)
                                                    global trial_counter
                                                    for i in trial.trial_dps:
                                                        if i in trial_counter.keys():
                                                            trial_counter[i] += 1
                                                        else:
                                                            trial_counter[i] = 1
                                                    for i in trial.trial_healers:
                                                        if i in trial_counter.keys():
                                                            trial_counter[i] += 1
                                                        else:
                                                            trial_counter[i] = 1
                                                    for i in trial.trial_tanks:
                                                        if i in trial_counter.keys():
                                                            trial_counter[i] += 1
                                                        else:
                                                            trial_counter[i] = 1
                                                    save_trial_count()
                                            except asyncio.TimeoutError:
                                                await ctx.send(f"{ctx.author.mention}, close has timed out")
                                                return
                                            del storage[num]
                                            save_to_doc()
                                            channel = ctx.guild.get_channel(num)
                                            if channel is not None:
                                                await ctx.guild.get_channel(num).delete()
                                            await ctx.send("Channel deleted, roster closed")
                                            logging.info("Deleted channel and closed roster ID: " + str(num))
                                            run = False
                                        else:
                                            await ctx.send("Unable to find trial.")
                                    else:
                                        if confirm == 'n':
                                            await ctx.send("Returning to menu.")
                                        else:
                                            await ctx.send("Invalid response, returning to menu.")
                            except IndexError:
                                await ctx.send("That is not a valid number, returning to menu.")
                        except ValueError:
                            await ctx.send("The input was not a valid number!")
            else:
                await ctx.send("You do not have permission to use this command")
        except Exception as e:
            logging.error("Close error: " + str(e))
            await ctx.send("An error has occurred in the command.")

    @commands.command(name="increase")
    async def increase_trial_count(self, ctx: commands.Context, member: discord.Member):
        """Officer command to increase someone's trial count by 1"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                global trial_counter
                if member.id in trial_counter.keys():
                    trial_counter[member.id] += 1
                    save_trial_count()
                    await ctx.send(f"Trial count for {member.display_name} is now {trial_counter.get(member.id)}")
                else:
                    trial_counter[member.id] = 1
                    save_trial_count()
                    await ctx.send(f"Trial count for {member.display_name} is now {trial_counter.get(member.id)}")
            else:
                await ctx.send("You do not have the permissions for this.")
        except Exception as e:
            await ctx.send("Unable to increase trial count")
            logging.error("Increase Trial Count Error: " + str(e))

    @commands.command(name="decrease")
    async def decrease_trial_count(self, ctx: commands.Context, member: discord.Member):
        """Officer command to decrease someone's trial count by 1"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                global trial_counter
                if member.id in trial_counter.keys():
                    if trial_counter[member.id] == 0:
                        await ctx.send("Trial Count cannot be less than 0")
                    else:
                        trial_counter[member.id] -= 1
                        save_trial_count()
                        await ctx.send(f"Trial count for {member.display_name} is now {trial_counter.get(member.id)}")
                else:
                    await ctx.send("User has no trials recorded.")
            else:
                await ctx.send("You do not have the permissions for this.")
        except Exception as e:
            await ctx.send("Unable to decrease trial count")
            logging.error("Decrease Trial Count Error: " + str(e))

    @commands.command(name="count")
    async def check_trial_count(self, ctx: commands.Context):
        """Check how many BOK trials you have been in since the bot started counting"""
        try:
            global trial_counter
            if ctx.author.id in trial_counter.keys():
                await ctx.reply(f"Total runs for {ctx.author.display_name} with BOK: {trial_counter.get(ctx.author.id)}"
                                )
            else:
                trial_counter[ctx.author.id] = 0
                await ctx.reply(f"Total runs for {ctx.author.display_name} with BOK: {trial_counter.get(ctx.author.id)}"
                                )
                save_trial_count()
        except Exception as e:
            await ctx.send("Unable to check your trial runs")
            logging.error("Check Trial Count Error: " + str(e))

    @commands.command(name="default")
    async def set_default_role(self, ctx: commands.Context, role="check"):
        """Set or check your default role to dps, healer, or tank when using !su. !default [optional: role]"""
        try:
            role = role.lower()
            global default_role
            if role == "dps" or role == "healer" or role == "tank":
                default_role[ctx.message.author.id] = role.lower()
                save_default_roles()
                await ctx.reply(f"{ctx.message.author.display_name} default role has been set to {role}")
            elif role == "check":
                if ctx.message.author.id in default_role.keys():
                    await ctx.reply(f"{ctx.message.author.display_name} defaults to "
                                    f"{default_role.get(ctx.message.author.id)}")
                else:
                    await ctx.reply("You do not have a default role. Use !default [role] to assign one.")
            elif role == "simp":
                default_role[ctx.message.author.id] == "healer"
                save_default_roles()
                role = discord.utils.get(ctx.guild.roles, name="Simp")
                await ctx.message.author.add_roles(role)
                await ctx.reply("Thank you, soft mommy dom, for you are now a simp.")
            else:
                await ctx.reply("Please specify the correct role. dps, healer, or tank.")
        except Exception as e:
            await ctx.send("Unable to set default role")
            logging.error("Default Role Set Error: " + str(e))

    @commands.command(name="setdef")
    async def admin_set_default_role(self, ctx: commands.Context, m: discord.Member, role="check"):
        """Officer way of manually assigning default roles"""
        try:
            officer = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in officer.members:
                global default_role
                if role.lower() == "dps" or role.lower() == "healer" or role.lower() == "tank":
                    default_role[m.id] = role.lower()
                    save_default_roles()
                    await ctx.reply(f"{m.display_name} default role has been set to {role}")

                elif role.lower() == "check":
                    if m.id in default_role.keys():
                        await ctx.reply(f"{m.display_name} defaults to {default_role.get(m.id)}")
                    else:
                        await ctx.reply("You do not have a default role. Use !default [role] to assign one.")

                else:
                    await ctx.reply("Please specify the correct role. dps, healer, or tank.")
            else:
                await ctx.reply("You do not have permission to do this")
        except Exception as e:
            await ctx.send("Unable to set default role")
            logging.error("Default Role Set Error: " + str(e))

    @commands.command(name="progrole")
    async def change_prog_role_name(self, ctx: commands.Context):
        """Officer way to adjust the week check"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name="Storm Bringers")
            user = ctx.message.author
            if user in role.members:
                global prog_role_name
                msg = ctx.message.content
                msg = msg.split(" ", 1)  # Split into 2 parts of a list, the first space then the rest
                msg = msg[1]
                prog_role_name = msg
                save_prog_name()
                await ctx.send("Prog role updated.")
            else:
                await ctx.send(f"You do not have permission to do this.")
        except Exception as e:
            await ctx.send("Unable to update prog role name")
            logging.error(f"Turn error: {str(e)}")


def setup(bot: commands.Bot):
    bot.add_cog(Raids(bot))
