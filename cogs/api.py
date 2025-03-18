from discord.ext import commands, tasks
import aiohttp

class Heartbeat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_task.start()

    @tasks.loop(seconds=30)
    async def api_task(self):
        async with aiohttp.ClientSession() as session:
            session.get(
                "https://kuma.janosch-bl.de/api/push/lQGf4Ei5vO?status=up&msg=OK&ping="
            )

def setup(bot):
    bot.add_cog(Heartbeat(bot))
