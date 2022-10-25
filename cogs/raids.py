import calendar
import datetime
import re
import discord
from discord.ext import commands
import logging
from pytz import timezone
from enum import Enum
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')

# Connect and get values from MongoDB
MONGODB_HOST = 'localhost'
MONGODB_PORT = 27017
client = MongoClient(MONGODB_HOST, MONGODB_PORT)
database = client['bot']  # Or do it with client.PyTest, accessing collections works the same way.
raids = database.raids
count = database.count
defaults = database.defaults


class Role(Enum):
    DPS = "dps"
    HEALER = "healer"
    TANK = "tank"
    NONE = "none"


class Raid:
    """Class to hold Raid information"""

    def __init__(self, raid, date, leader, dps={}, healers={}, tanks={}, backup_dps={}, backup_healers={},
                 backup_tanks={}, dps_limit=0, healer_limit=0, tank_limit=0, role_limit=0):
        self.raid = raid
        self.date = date
        self.leader = leader
        self.dps = dps
        self.tanks = tanks
        self.healers = healers
        self.backup_dps = backup_dps
        self.backup_tanks = backup_tanks
        self.backup_healers = backup_healers
        self.dps_limit = dps_limit
        self.tank_limit = tank_limit
        self.healer_limit = healer_limit
        self.role_limit = role_limit

    def get_data(self):
        all_data = {
            "raid": self.raid,
            "date": self.date,
            "leader": self.leader,
            "dps": self.dps,
            "healers": self.healers,
            "tanks": self.tanks,
            "backup_dps": self.backup_dps,
            "backup_healers": self.backup_healers,
            "backup_tanks": self.backup_tanks,
            "dps_limit": self.dps_limit,
            "healer_limit": self.healer_limit,
            "tank_limit": self.tank_limit,
            "role_limit": self.role_limit
        }
        return all_data

    # Add people into the right spots
    def add_dps(self, n_dps, p_class=""):
        if len(self.dps) < self.dps_limit:
            self.dps[n_dps] = p_class
        else:
            self.backup_dps[n_dps] = p_class

    def add_healer(self, n_healer, p_class=""):
        if len(self.healers) < self.healer_limit:
            self.healers[n_healer] = p_class
        else:
            self.backup_healers[n_healer] = p_class

    def add_tank(self, n_tank, p_class=""):
        if len(self.tanks) < self.tank_limit:
            self.tanks[n_tank] = p_class
        else:
            self.backup_tanks[n_tank] = p_class

    def add_backup_dps(self, n_dps, p_class=""):
        self.backup_dps[n_dps] = p_class

    def add_backup_healer(self, n_healer, p_class=""):
        self.backup_healers[n_healer] = p_class

    def add_backup_tank(self, n_tank, p_class=""):
        self.backup_tanks[n_tank] = p_class

    # remove people from right spots
    def remove_dps(self, n_dps):
        if n_dps in self.dps:
            del self.dps[n_dps]
        else:
            del self.backup_dps[n_dps]

    def remove_healer(self, n_healer):
        if n_healer in self.healers:
            del self.healers[n_healer]
        else:
            del self.backup_healers[n_healer]

    def remove_tank(self, n_tank):
        if n_tank in self.tanks:
            del self.tanks[n_tank]
        else:
            del self.backup_tanks[n_tank]

    def change_role_limit(self, new_role_limit):
        self.role_limit = new_role_limit

    def change_dps_limit(self, new_dps_limit):
        self.dps_limit = new_dps_limit

    def change_healer_limit(self, new_healer_limit):
        self.healer_limit = new_healer_limit

    def change_tank_limit(self, new_tank_limit):
        self.tank_limit = new_tank_limit

    def fill_spots(self, num):
        try:
            loop = True
            while loop:
                if len(self.dps) < self.dps_limit and len(self.backup_dps) > 0:
                    first = list(self.backup_dps.keys())[0]
                    self.dps[first] = self.backup_dps.get(first)
                    del self.backup_dps[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.healers) < self.healer_limit and len(self.backup_healers) > 0:
                    first = list(self.backup_healers.keys())[0]
                    self.healers[first] = self.backup_healers.get(first)
                    del self.backup_healers[first]
                else:
                    loop = False
            loop = True
            while loop:
                if len(self.tanks) < self.tank_limit and len(self.backup_tanks) > 0:
                    first = list(self.backup_tanks.keys())[0]
                    self.tanks[first] = self.backup_tanks.get(first)
                    del self.backup_tanks[first]
                else:
                    loop = False
            logging.info(f"Spots filled in raid id {str(num)}")
        except Exception as e:
            logging.error(f"Fill Spots error: {str(e)}")


class Raids(commands.Cog, name="Raids"):
    """Commands related to Raids"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="raid", aliases=["trial"])
    async def create_roster(self, ctx: commands.Context):
        """Created a new roster"""
        try:
            role = discord.utils.get(ctx.message.author.guild.roles, name=self.bot.config['raids']['lead'])
            if role != "@everyone" and ctx.message.author not in role.members:
                await ctx.reply(f"You do not have permission to use this command")
                return
        except Exception as e:
            await ctx.send(f"Unable to verify roles, check that the config is spelled the same as the discord role.")
            logging.error(f"creation error on role verification: {str(e)}")

        def suffix(d):
            try:
                return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')
            except Exception as e2:
                ctx.send(f"Error on setting the suffix.")
                logging.error(f"Suffix Failure: {str(e2)}")

        def factory(fact_leader, fact_raid, fact_date, fact_dps_limit, fact_healer_limit, fact_tank_limit,
                    fact_role_limit):
            try:
                if fact_dps_limit is None and fact_healer_limit is None and fact_tank_limit is None:
                    fact_dps_limit = self.bot.config["raids"]["roster_defaults"]["dps"]
                    fact_healer_limit = self.bot.config["raids"]["roster_defaults"]["healers"]
                    fact_tank_limit = self.bot.config["raids"]["roster_defaults"]["tanks"]
                if fact_role_limit == 0:
                    fact_role_limit = self.bot.config["raids"]["roles"]["base"]
                elif fact_role_limit == 1:
                    fact_role_limit = self.bot.config["raids"]["roles"]["first"]
                elif fact_role_limit == 2:
                    fact_role_limit = self.bot.config["raids"]["roles"]["second"]
                elif fact_role_limit == 3:
                    fact_role_limit = self.bot.config["raids"]["roles"]["third"]
                elif fact_role_limit == 4:
                    fact_role_limit = self.bot.config["raids"]["roles"]["fourth"]
                else:
                    ctx.reply("Error: Somehow the code reached this in theory unreachable spot. Time to panic!")
                    logging.error("You done goofed.")

                dps, healers, tanks, backup_dps, backup_healers, backup_tanks = {}, {}, {}, {}, {}, {}
                return Raid(fact_raid, fact_date, fact_leader, dps, healers, tanks, backup_dps, backup_healers,
                            backup_tanks, fact_dps_limit, fact_healer_limit, fact_tank_limit, fact_role_limit)
            except Exception as e2:
                ctx.send(f"Error on getting the role limits, please check the config is correct")
                logging.error(f"Factory Failure: {str(e2)}")

        try:
            msg = ctx.message.content
            msg = msg.split(" ", 1)  # Split into 2 parts of a list, the first space then the rest
            vals = msg[1].split(",")  # drop the command
            # Check whether the bot creates limits for the roster or not
        except Exception as e:
            await ctx.send("Error: Unable to separate values from command input")
            logging.error(f"Raid Creation Error: {str(e)}")
        try:
            if self.bot.config['raids']['use_limits']:
                if len(vals) == 7:
                    leader, raid, date, dps_limit, healer_limit, tank_limit, role_limit = vals
                    if 0 > role_limit > 3:
                        await ctx.send(f"Invalid input, the role_limits must be between 0 and 4")
                    date_info = int(re.sub('[^0-9]', '', date))
                    created = factory(leader, raid, date_info, dps_limit, healer_limit, tank_limit, role_limit)
                elif len(vals) == 4:
                    leader, raid, date, role_limit = vals
                    if 0 > role_limit > 3:
                        await ctx.send(f"Invalid input, the role_limits must be between 0 and 4")
                    dps_limit, healer_limit, tank_limit = None, None, None
                    date_info = int(re.sub('[^0-9]', '', date))
                    created = factory(leader, raid, date_info, dps_limit, healer_limit, tank_limit, role_limit)
                else:
                    if len(vals) > 7:
                        await ctx.reply(f"Invalid input, you have too many parameters.")
                        return
                    elif len(vals) > 4:
                        await ctx.reply(f"Invalid input, if you want to specify the limits you have too few parameters."
                                        f" If you do not then you have too many.")
                        return
                    else:
                        await ctx.reply("Invalid input, you have too few parameters.")
                        return
            else:
                if len(vals) == 6:
                    leader, raid, date, dps_limit, healer_limit, tank_limit = vals
                    date_info = int(re.sub('[^0-9]', '', date))
                    created = factory(leader, raid, date_info, dps_limit, healer_limit, tank_limit, 0)
                elif len(vals) == 3:
                    leader, raid, date = vals
                    dps_limit, healer_limit, tank_limit = None, None, None
                    date_info = int(re.sub('[^0-9]', '', date))
                    created = factory(leader, raid, date_info, dps_limit, healer_limit, tank_limit, 0)
                else:
                    await ctx.reply("Role Limits are not configured, please do not include them.")
                    logging.info(f"Attempted to create roster with role limits that are not configured.")
                    return
        except Exception as e:
            await ctx.send(f"Raid Creation Error: {str(e)}")

        try:
            logging.info(f"Creating new channel.")
            category = ctx.guild.get_channel(self.bot.config["raids"]["category"])
            new_time = datetime.datetime.utcfromtimestamp(date_info)
            tz = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(
                tz=timezone(self.bot.config["raids"]["timezone"]))
            weekday = calendar.day_name[tz.weekday()]
            day = tz.day
            new_name = created.raid + "-" + weekday + "-" + str(day) + suffix(day)
            channel = await category.create_text_channel(new_name)

            embed = discord.Embed(
                title=created.raid + " " + "<t:" + str(created.date) + ":f>",
                description="I hope people sign up for this.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Remember to spay or neuter your support!")
            embed.set_author(name="Raid Lead: " + leader)
            embed.add_field(name="Calling Healers!", value='To Heal Us!', inline=False)
            embed.add_field(name="Calling Tanks!", value='To Be Stronk!', inline=False)
            embed.add_field(name="Calling DPS!", value='To Stand In Stupid!', inline=False)
            await channel.send(embed=embed)
            await ctx.reply("Channel and Roster created")
            logging.info(f"Created Channel: channelID: {str(channel.id)}")
        except Exception as e:
            await ctx.send(
                f"Error in creating category channel and sending embed. Please make sure config is correct and"
                " perms for the bot are set to allow this to take place.")
            logging.error(f"Raid Creation Channel And Embed Error: {str(e)}")

        # Save raid info to MongoDB
        try:
            logging.info(f"Saving Roster channelID: {str(channel.id)}")
            rec = {
                'channelID': channel.id,
                'data': created.get_data()
            }
            raids.insert_one(rec)
            logging.info(f"Saved Roster channelID: {str(channel.id)}")
        except Exception as e:
            await ctx.send("Error in saving information to MongoDB, roster was not saved.")
            logging.error(f"Raid Creation MongoDB Error: {str(e)}")

    @commands.command()
    async def su(self, ctx: commands.Context):
        """Signs you up to a roster"""
        try:
            channel = ctx.message.channel.id
            try:
                rec = raids.find_one({'channelID': channel})
                if rec is None:
                    await ctx.reply("You are not in a raid roster channel")
                    return
                raid = Raid(rec['data']['raid'], rec['data']['date'], rec['data']['leader'], rec['data']['dps'],
                            rec['data']['healers'], rec['data']['tanks'], rec['data']['backup_dps'],
                            rec['data']['backup_healers'], rec['data']['backup_tanks'], rec['data']['dps_limit'],
                            rec['data']['healer_limit'], rec['data']['tank_limit'], rec['data']['role_limit'])
            except Exception as e:
                await ctx.send("Unable it load raid.")
                logging.error(f"SU Load Raid Error: {str(e)}")
                return

            if self.bot.config['raids']['use_limits'] is True:
                limiter = discord.utils.get(ctx.message.author.guild.roles, name=raid.role_limit)
                if ctx.message.author not in limiter.members:
                    await ctx.reply("You do not have the role to join this roster.")
                    return

            single = False  # A variable to check if someone just used !su
            msg = ctx.message.content
            msg = msg.split(" ", 2)
            if len(msg) == 1:
                single = True
            user_id = str(ctx.message.author.id)
            worked = False
            slotted = Role.NONE
            msg_change = False
            og_msg = ""
            default = ""
            # Check if the user has a default set or at least specified one.
            try:
                default = defaults.find_one({'userID': user_id})
                if default is None and single is True:
                    await ctx.reply("You have no default set, please specify a role or set a default.")
                    return
                elif default is None and single is False:
                    role = msg[1].lower()
                    if role != "dps" and role != "healer" and role != "tank":
                        await ctx.reply("You have no default set, please specify a role or set a default.")
                        return
            except Exception as e:
                await ctx.send("Unable to check user default data.")
                logging.error(f"SU Error: Unable to fetch user default data: {str(e)}")
                return

            # Check if the user swapped their role
            try:
                if user_id in raid.dps.keys():
                    og_msg = raid.dps.get(user_id)
                    print(og_msg)
                    slotted = Role.DPS
                    raid.remove_dps(user_id)

                elif user_id in raid.backup_dps.keys():
                    og_msg = raid.backup_dps.get(user_id)
                    raid.remove_dps(user_id)
                    slotted = Role.DPS

                elif user_id in raid.healers.keys():
                    og_msg = raid.healers.get(user_id)
                    raid.remove_healer(user_id)
                    slotted = Role.HEALER

                elif user_id in raid.backup_healers.keys():
                    og_msg = raid.backup_healers.get(user_id)
                    raid.remove_healer(user_id)
                    slotted = Role.HEALER

                elif user_id in raid.tanks.keys():
                    og_msg = raid.tanks.get(user_id)
                    raid.remove_tank(user_id)
                    slotted = Role.TANK

                elif user_id in raid.backup_tanks.keys():
                    og_msg = raid.backup_tanks.get(user_id)
                    raid.remove_tank(user_id)
                    slotted = Role.TANK

                # Just along check to verify it is not any of the defaults or empty first dps then healer then tank
                if slotted != Role.NONE and og_msg != "":
                    msg_change = True
                    # Now that we have determined that the original message is not default, need to adjust accordingly
                    #   in non-role change situations. IE: just calling !su or !bu to swap which roster they are on
            except Exception as e:
                await ctx.send("Unable to verify roster information")
                logging.error(f"SU Error Roster Swap Data: {str(e)}")
                return
            try:
                if not single:
                    role = msg[1].lower()
                    if role == "dps" or role == "healer" or role == "tank":
                        # Check if there is an optional message or not
                        if len(msg) == 3:
                            # The message has a SU, a Role, and a message. Now to grab the right role
                            if role == "dps":
                                raid.add_dps(user_id, msg[2])
                                worked = True
                            elif role == "healer":
                                raid.add_healer(user_id, msg[2])
                                worked = True
                            elif role == "tank":
                                raid.add_tank(user_id, msg[2])
                                worked = True
                        else:
                            # The message has a SU and a Role
                            if role == "dps":
                                if slotted == Role.DPS and msg_change:
                                    raid.add_dps(user_id, og_msg)
                                else:
                                    raid.add_dps(user_id)
                                worked = True
                            elif role == "healer":
                                if slotted == Role.HEALER and msg_change:
                                    raid.add_healer(user_id, og_msg)
                                else:
                                    raid.add_healer(user_id)
                                worked = True
                            elif role == "tank":
                                if slotted == Role.TANK and msg_change:
                                    raid.add_tank(user_id, og_msg)
                                else:
                                    raid.add_tank(user_id)
                                worked = True
                    else:
                        # No role, need to grab default
                        if len(msg) == 3:
                            msg = msg[1] + " " + msg[2]  # merge together the message if needed
                        else:
                            msg = msg[1]
                        role = default.get(user_id)
                        if role == "dps":
                            raid.add_dps(user_id, msg)
                            worked = True
                        elif role == "healer":
                            raid.add_healer(user_id, msg)
                            worked = True
                        elif role == "tank":
                            raid.add_tank(user_id, msg)
                            worked = True
                else:
                    # User just called !su, no message, no role
                    role = default.get(user_id)
                    if role == "dps":
                        if slotted == Role.DPS and msg_change:
                            raid.add_dps(user_id, og_msg)
                        else:
                            raid.add_dps(user_id)
                        worked = True
                    elif role == "healer":
                        if slotted == Role.HEALER and msg_change:
                            raid.add_healer(user_id, og_msg)
                        else:
                            raid.add_healer(user_id)
                        worked = True
                    elif role == "tank":
                        if slotted == Role.TANK and msg_change:
                            raid.add_tank(user_id, og_msg)
                        else:
                            raid.add_tank(user_id)
                        worked = True
            except Exception as e:
                await ctx.send("I was unable to put you in the roster")
                logging.error(f"SU Error Put In Roster: {str(e)}")
                return

            try:
                if worked is True:
                    logging.info(f"Updating Roster channelID: {channel}")
                    new_rec = {'$set': {'data': raid.get_data()}}
                    raids.update_one({'channelID': channel}, new_rec)
                    logging.info(f"Roster channelID: {channel} updated")
            except Exception as e:
                await ctx.send("I was unable to save the updated roster.")
                logging.error(f"SU Error saving new roster: {str(e)}")
                return
            await ctx.reply("Added!")
        except Exception as e:
            await ctx.send(f"I was was unable to sign you up due to processing errors.")
            logging.error(f"SU Error: {str(e)}")
            return



    @commands.command()
    async def get(self, ctx: commands.Context):
        raid = raids.find_one({'channelID': 942870073629110313})
        print(raid["data"]['raid'])

    @commands.command()
    async def up(self, ctx: commands.Context):
        rec = raids.find_one({'channelID': 942870073629110313})
        update = Raid(rec['data']['raid'], rec['data']['date'], rec['data']['leader'], rec['data']['dps'],
                      rec['data']['healers'], rec['data']['tanks'], rec['data']['backup_dps'],
                      rec['data']['backup_healers'], rec['data']['backup_tanks'], rec['data']['dps_limit'],
                      rec['data']['healer_limit'], rec['data']['tank_limit'], rec['data']['role_limit'])
        update.leader = "You"

        new_rec = {'$set': {'data': update.get_data()}}
        raids.update_one({'channelID': 942870073629110313}, new_rec)

    # TODO: For Status Update Need To convert user ID from str to int
    # TODO: For menu-based options where you select an item, consider creating a new collection to store the channels
    #   maybe? Will need to explore this option.


async def setup(bot: commands.Bot):
    await bot.add_cog(Raids(bot))
