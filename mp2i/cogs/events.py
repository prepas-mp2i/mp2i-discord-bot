import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog
from sqlalchemy import delete

from mp2i.models import GuildModel
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper
from mp2i.wrappers.message import MessageWrapper

logger = logging.getLogger(__name__)


class EventsCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self) -> None:
        """
        When client is connected
        """
        print(f"\n{' READY ':>^80}\n")

    @Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """
        Log message in database and update message count
        """
        MessageWrapper(msg).insert()
        member = MemberWrapper(msg.author)
        member.messages_count += 1

    @Cog.listener()
    async def on_guild_join(self, guild) -> None:
        """
        When client is invited to a guild, register all members in database
        """
        guild = GuildWrapper(guild)
        guild.register()

        for member in map(MemberWrapper, guild.members):
            member.register()
            for role in member.roles:
                if role.id in guild.config.roles:
                    member.update(role=role.name)

    @Cog.listener()
    async def on_guild_remove(self, guild) -> None:
        """
        When client is removed from a guild
        """
        database.execute(delete(GuildModel).where(GuildModel.id == guild.id))

    @Cog.listener()
    async def on_member_join(self, member) -> None:
        """
        When a member join a guild, insert it in database or restore its roles
        """
        member = MemberWrapper(member)
        if not member.exists():
            member.register()
        elif member.role:
            await member.add_roles(
                member.role,
                reason="The user was already register, re-assign its role",
            )

        text = f"{member.mention} a rejoint le serveur {member.guild.name}!"
        embed = discord.Embed(
            title="Arriv??e d'un membre!",
            colour=0xFF22FF,
            description=text,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_author(name=member.name, url=member.avatar.url)
        embed.set_footer(text=f"{self.bot.user.name}")

        if member.guild.system_channel:
            await member.guild.system_channel.send(embed=embed)
        else:
            logger.warning("System channel is not set")

    @Cog.listener()
    async def on_member_update(self, before, after) -> None:
        """
        Check if a member has updated roles and modifies them in the database
        """
        if before.roles == after.roles:
            return

        member = MemberWrapper(after)
        guild = GuildWrapper(after.guild)
        if not member.exists():
            logger.warning(f"The user {after.name} was not a registered member")
            member.register()

        for role in after.roles:
            if role.id in guild.config.roles:
                member.update(role=role.name)
                break
        else:
            member.update(role=None)


async def setup(bot) -> None:
    await bot.add_cog(EventsCog(bot))
