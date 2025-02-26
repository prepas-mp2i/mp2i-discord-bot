import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog
from sqlalchemy import delete

from mp2i.models import GuildModel
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

logger = logging.getLogger(__name__)


class EventsCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self) -> None:
        """
        When client is connected, sync the command tree.
        """
        await self.bot.tree.sync()  # Sync the command tree

        for guild in map(GuildWrapper, self.bot.guilds):
            if not guild.exists():
                guild.register()
            for member in map(MemberWrapper, guild.members):
                if not member.exists():
                    member.register()

        print(f"\n{' READY ':>^80}\n")

    @Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """
        Log message in database and update message count
        """
        member = MemberWrapper(msg.author)
        if member.exists():
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

        text = f"{member.mention} a rejoint le serveur {member.guild.name}!"
        embed = discord.Embed(
            title="Arrivée d'un membre!",
            colour=0xFF22FF,
            description=text,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_author(name=member.mention)
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
        if before.roles == after.roles or not (member := MemberWrapper(after)).exists():
            return

        for qualifier in GuildWrapper(after.guild).choiceable_roles:
            if discord.utils.get(after.roles, name=qualifier):
                return member.update(role=qualifier)

    @Cog.listener()
    async def on_message_delete(self, msg: discord) -> None:
        """
        When a message is deleted, send logs in the log channel
        """
        guild = GuildWrapper(msg.guild)
        if not guild.log_channel:
            return

        if msg.channel == guild.admin_channel or msg.author.bot:
            return

        embed = discord.Embed(
            title="Message supprimé",
            colour=0xED0010,
            timestamp=datetime.now(),
        )
        embed.add_field(name="Auteur", value=msg.author.mention)
        embed.add_field(name="Salon", value=msg.channel.mention)
        embed.add_field(
            name="Message original", value=f">>> {msg.content}", inline=False
        )
        embed.set_footer(text=self.bot.user.name)
        await guild.log_channel.send(embed=embed)

    @Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        """
        When a message is edited, send logs in the log channel
        """
        guild = GuildWrapper(before.guild)
        if not before.guild or not (log_chan := guild.log_channel):
            return
        
        if before.channel == guild.admin_channel or before.author.bot:
            return

        embed = discord.Embed(
            title="Message modifié",
            colour=0x6DD7FF,
            timestamp=datetime.now(),
        )
        embed.add_field(name="Auteur", value=before.author.mention)
        embed.add_field(name="Lien du nouveau message", value=after.jump_url)
        embed.add_field(
            name="Message original", value=f">>> {before.content}", inline=False
        )
        embed.set_footer(text=self.bot.user.name)
        await log_chan.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(EventsCog(bot))
