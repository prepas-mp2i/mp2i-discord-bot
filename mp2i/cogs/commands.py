import logging
from itertools import cycle
from typing import Optional

import discord
from discord.ext import tasks
from discord.ext.commands import Cog, command, guild_only, is_owner, has_role
from sqlalchemy import func, select

from mp2i.utils import database
from mp2i.wrappers.guild import GuildWrapper
from mp2i.models import MessageModel

from .utils import youtube

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
        Supprime les n derniers messages du salon
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

    @command(aliases=["member_info"])
    @guild_only()
    async def profile(self, ctx, member: Optional[discord.Member] = None) -> None:
        """
        Consulter les infos d'un membre
        """
        if not member:
            member = ctx.author

        embed = discord.Embed(title="Profil", colour=0xFFA325)
        embed.set_author(name=member.name)
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="Pseudo", value=member.mention, inline=True)
        embed.add_field(
            name="Membre depuis", value=f"{member.joined_at:%d/%m/%Y}", inline=True
        )
        number_of_messages = database.execute(
            select([func.count(MessageModel.id)],
                   MessageModel.author_id == member.id)
        ).scalar_one()
        embed.add_field(name="Messages", value=number_of_messages, inline=True)
        embed.add_field(
            name="Rôles",
            inline=True,
            value=" ".join(
                r.mention for r in member.roles if r.name != "@everyone"),
        )
        await ctx.send(embed=embed)

    @command(aliases=["server_profile"])
    @guild_only()
    async def server_info(self, ctx) -> None:
        """
        Consulter les infos du serveur
        """
        guild = GuildWrapper(ctx.guild)
        embed = discord.Embed(title="Infos du serveur", colour=0xFFA325)
        embed.set_author(name=guild.name)
        embed.set_thumbnail(url=guild.icon_url)
        embed.add_field(name="Membres", value=len(guild.members), inline=True)

        for role_id, role in guild.config.roles.items():
            number = len(guild.get_role(role_id).members)
            embed.add_field(name=f"{role['name']}", value=number, inline=True)
        await ctx.send(embed=embed)

    @command()
    @guild_only()
    async def referents(self, ctx) -> None:
        """
        Liste les étudiants référents du serveur
        """
        message = f"Liste des étudiants référents du serveur {ctx.guild.name}:\n"
        for member in ctx.guild.members:
            if discord.utils.get(member.roles, name="Référent"):
                message += f"- {member.mention} - ({member.status})\n"
        await ctx.send(message,
                       allowed_mentions=discord.AllowedMentions(users=False))


def setup(bot) -> None:
    bot.add_cog(Commands(bot))
