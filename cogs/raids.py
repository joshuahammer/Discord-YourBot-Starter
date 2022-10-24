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

        def factory(fact_leader, fact_raid, fact_date, fact_dps_limit, fact_healer_limit, fact_tank_limit, fact_role_limit):
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
            category = ctx.guild.get_channel(self.bot.config["raids"]["category"])
            new_time = datetime.datetime.utcfromtimestamp(date_info)
            tz = new_time.replace(tzinfo=datetime.timezone.utc).astimezone(tz=timezone(self.bot.config["raids"]["timezone"]))
            weekday = calendar.day_name[tz.weekday()]
            day = tz.day
            new_name = created.raid + "-" + weekday + "-" + str(day) + suffix(day)
            channel = await category.create_text_channel(new_name)

            embed = discord.Embed(
                title=created.raid + " " + "<t:"+str(created.date)+":f>",
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
        except Exception as e:
            await ctx.send("Error in creating category channel and sending embed. Please make sure config is correct and"
                           " perms for the bot are set to allow this to take place.")
            logging.error(f"Raid Creation Channel And Embed Error: {str(e)}")

        # Save raid info to MongoDB
        try:
            rec = {
                'channelID': channel.id,
                'data': created.get_data()
            }
            raids.insert_one(rec)
        except Exception as e:
            await ctx.send("Error in saving information to MongoDB, roster was not saved.")
            logging.error(f"Raid Creation MongoDB Error: {str(e)}")

    @commands.command()
    async def put(self, ctx: commands.Context):
        raid_test = Raid("test", 45, "Me", {'14223432': 'dps'}, {'14223432': 'tank'}, {'14223432': 'healer'}, {}, {},
                         {}, 8,
                         2, 2, 0)
        print(f"{raid_test.get_data()}")
        print(f"Attempting to talk to MongoDB")
        rec = {
            'channelID': 942870073629110313,
            'data': raid_test.get_data()
        }
        raids.insert_one(rec)

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


async def setup(bot: commands.Bot):
    await bot.add_cog(Raids(bot))
