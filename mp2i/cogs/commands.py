import logging
from itertools import cycle
from typing import Optional

import discord
from discord.ext import tasks
from discord.ext.commands import Cog, command, guild_only, is_owner, has_role

from .utils import youtube
from mp2i.wrappers.member import MemberWrapper

logger = logging.getLogger(__name__)


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status = cycle((discord.Game(name=f"{bot.command_prefix}help"),))

    @command(name="status")
    @guild_only()
    @is_owner()
    async def change_status(self, ctx, *, query: str) -> None:
        """
        Change le status du bot par des vidéos correspondantes à la recherche
        """
        videos = []
        for video in youtube.search(query, n=50):
            videos.append(discord.Streaming(**video))

        if len(videos) > 0:
            self.status = cycle(videos)
        else:
            await ctx.send("Aucune vidéo n'a été trouvée")

    @tasks.loop(seconds=30)
    async def loop_status(self) -> None:
        try:
            await self.bot.change_presence(activity=next(self.status))
        except discord.errors.HTTPException:
            logger.error("Can't change bot presence")

    @Cog.listener("on_ready")
    async def before_loop_status(self) -> None:
        self.loop_status.start()

    @command()
    @guild_only()
    @has_role("Administrateurs")
    async def clear(self, ctx, n: int = 1) -> None:
        """
        Supprime les n messages du salon
        """
        await ctx.channel.purge(limit=int(n) + 1)

    @command()
    @guild_only()
    async def send(self, ctx, *, message: str) -> None:
        """
        Envoie un message dans le salon actuel
        """
        await ctx.send(message)
        await ctx.message.delete()

    @command(name="profile", aliases=["member_info"])
    @guild_only()
    async def profile(self, ctx, member: Optional[MemberWrapper] = None) -> None:
        """
        Consulter les infos d'un membre
        """
        if not member:
            member = MemberWrapper(ctx.author)

        embed = discord.Embed(title="Profil", colour=0xFFA325)
        embed.set_author(name=member.name)
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="Name", value=member.mention, inline=True)
        embed.add_field(
            name="Membre depuis...", value=f"{member.joined_at:%d/%m/%Y}", inline=True
        )
        if member.role:
            embed.add_field(name="Rôle", value=member.role.name, inline=True)
        await ctx.send(embed=embed)


def setup(bot) -> None:
    bot.add_cog(Commands(bot))
