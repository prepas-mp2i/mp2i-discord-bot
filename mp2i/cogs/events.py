import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog
from sqlalchemy import insert, delete

from mp2i.models import GuildModel
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.message import MessageWrapper

from .utils.functions import get_reactions_values

logger = logging.getLogger(__name__)


class EventsCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        """
        When client is connected
        """
        print(f"\n{' READY ':>^80}\n")

    @Cog.listener()
    async def on_guild_join(self, guild):
        """
        When client is invited to a guild
        """
        database.execute(insert(GuildModel).values(id=guild.id, name=guild.name))
        for member in guild.members:
            MemberWrapper(member).register()

    @Cog.listener()
    async def on_guild_remove(self, guild):
        """
        When client is removed from a guild
        """
        database.execute(delete(GuildModel).where(GuildModel.id == guild.id))

    @Cog.listener()
    async def on_member_join(self, member):
        """
        When a member join a guild, insert it in database or restore all its data
        """
        member = MemberWrapper(member)
        if member.exists():
            await member.add_roles(
                member.role,
                reason="The user was already register, re-attribute the main role",
            )
        else:
            member.register()

        text = f"{member.mention} a rejoint le serveur {member.guild.name}!"
        embed = discord.Embed(
            title="Arrivée d'un membre!",
            colour=0xFF22FF,
            description=text,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_author(name=member.name, url=member.avatar_url)
        embed.set_footer(text=f"{self.bot.user.name}")

        news_channel = discord.utils.get(member.guild.channels, type="news")
        if news_channel:
            await news_channel.send(embed=embed)
        else:
            logger.warning("Server doesn't have a news channel")

    @Cog.listener()
    async def on_message(self, msg):
        """
        Log message in database and obtain few XP
        """
        MessageWrapper(msg).insert()

    @Cog.listener()
    async def on_member_update(self, before, after):
        """
        Check if a member has updated roles and modifies them in the database
        """
        if before.roles == after.roles:
            return

        member = MemberWrapper(after)
        if not member.exists():
            logger.error(f"The user {after.name} was not found in members table")

        for role in after.roles:
            if role.name in get_reactions_values():
                member.role = role
                break
        else:
            member.role = None


def setup(bot):
    bot.add_cog(EventsCog(bot))
