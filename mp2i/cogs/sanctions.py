import discord
from discord.ext.commands import Cog, command, guild_only


class Sanction(Cog):
    """
    Offers interface to manage sanctions to users
    """

    def __init__(self, bot):
        self.bot = bot

    @command(name="warn")
    @guild_only()
    async def warn(self, ctx, member: discord.Member, *, raison: str, mp: str = "oui",
                   visible: str = "non") -> None:
        pass


async def setup(bot) -> None:
    await bot.add_cog(Sanction(bot))