import discord
from discord.ext import commands, tasks
import random
import logging
import datetime
import calendar

# For using Aliases: (name="ex", aliases=["al1", "al2"])

logging.basicConfig(level=logging.INFO, format='%(asctime)s: %(message)s')


class Fun(commands.Cog, name="Fun Things"):
    """For Fun/Event Type Things"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scheduled_good_morning.start()

    @commands.command()
    async def f(self, ctx: commands.Context):
        """F"""
        await ctx.send('https://tenor.com/view/keyboard-hyperx-rgb-hyperx-family-hyperx-gaming-gif-17743649')

    @commands.command(name="8ball")
    async def magic_eight_ball(self, ctx: commands.context):
        """Answers a question like a magic 8-ball"""
        # responses from here: https://en.wikipedia.org/wiki/Magic_8-ball#Possible_answers
        try:
            ran = random.randint(1, 20)
            response = ""
            match ran:
                case 1:
                    response = "It is certain."
                case 2:
                    response = "It is decidedly so."
                case 3:
                    response = "Without a doubt."
                case 4:
                    response = "Yes definitely."
                case 5:
                    response = "You may rely on it."
                case 6:
                    response = "As I see it, yes."
                case 7:
                    response = "Most likely."
                case 8:
                    response = "Outlook good."
                case 9:
                    response = "Yes."
                case 10:
                    response = "Signs point to yes."
                case 11:
                    response = "Reply hazy, try again."
                case 12:
                    response = "Ask again later."
                case 13:
                    response = "Better not tell you now."
                case 14:
                    response = "Cannot predict now."
                case 15:
                    response = "Concentrate and ask again."
                case 16:
                    response = "Don't count on it."
                case 17:
                    response = "My reply is no."
                case 18:
                    response = "My sources say no."
                case 19:
                    response = "Outlook not so good."
                case 20:
                    response = "Very doubtful. "
            if ran % 2 == 1:
                ran = random.randint(1, 10)  # Give this a like 1 in 10 chance of showing up if the number is odd
                if ran == 2:
                    response = "Fuck off I am sleeping."

            await ctx.reply(response)
        except Exception as e:
            await ctx.send("Unable to use the magic, something is blocking it!")
            logging.error("Magic 8 Ball Error: " + str(e))

    @tasks.loop(time=datetime.time(13, 0, 0, 0))  # UTC Time, remember to convert and use a 24 hour-clock.
    async def scheduled_good_morning(self):
        try:
            guild = self.bot.config['guild']
            channel = self.bot.config['morning']
            await channel.send("Good Morning!")
            try:
                today = datetime.datetime.today()
                today_month = today.month
                today_day = today.day
                today_year = today.year
                for member in guild.members:
                    joined = member.joined_at
                    joined_month = joined.month
                    joined_day = joined.day
                    joined_year = joined.year
                    if today_month == joined_month and today_day == joined_day and today_year > joined_year:
                        await channel.send(f"{member.mention} Happy Anniversary!")
            except Exception as e:
                await channel.send("Unable to get the Anniversaries.")
                logging.error(f"Good Morning Task Anniversary Error: {str(e)}")
        except Exception as e:
            logging.error(f"Good Morning Task Error: {str(e)}")

    @commands.command()
    async def joined(self, ctx: commands.context, m: discord.Member = None):
        """Tells you when you joined the server in M-D-Y Format"""
        try:
            def suffix(d):
                return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

            if m is None:
                user = ctx.message.author
                await ctx.reply(f"According to the records you joined {ctx.guild.name} on "
                                f"{calendar.month_name[user.joined_at.month]} {user.joined_at.day}"
                                f"{suffix(user.joined_at.day)} {user.joined_at.year}")
            else:
                await ctx.reply(f"According to the records {m.display_name} joined {ctx.guild.name} on "
                                f"{calendar.month_name[m.joined_at.month]} {m.joined_at.day}"
                                f"{suffix(m.joined_at.day)} {m.joined_at.year}")
        except Exception as e:
            logging.error("Joined command error: " + str(e))
            await ctx.send("Unable to fetch joined information.")

    @commands.command(name="wrap")
    async def create_bubblewrap(self, ctx: commands.context):
        """For all your popping needs"""
        message = f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n" \
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n" \
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||\n" \
                  f"||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop|| ||pop||"
        await ctx.send(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
