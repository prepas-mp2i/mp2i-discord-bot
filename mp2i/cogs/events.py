import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog
from sqlalchemy import insert

from mp2i.models import GuildModel
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.message import MessageWrapper


class EventsCog(Cog):
    WELCOME_CHANNEL = "📢annonces"

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

    @Cog.listener()
    async def on_member_join(self, member):
        """
        When a member join a guild, insert it in database or restore all its data
        """
        member = MemberWrapper(member)
        if member.exists():
            await member.add_roles(
                member.sub_roles | {member.role},  # union
                reason="The user was already register, re-attribute the main role",
            )
        else:
            member.register()
            default_role = member.guild.get_role_by_name("Non Vérifié")
            await member.add_roles(default_role, reason="User was not verified")

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

        publish_channel = discord.utils.get(
            member.guild.channels, name=self.WELCOME_CHANNEL
        )
        await publish_channel.send(embed=embed)

    @Cog.listener()
    async def on_message(self, msg):
        """
        Log message in database and obtain few XP
        """
        if not msg.author.bot:
            MessageWrapper(msg).insert()
        if isinstance(msg.channel, discord.TextChannel):
            try:
                mod_member = MemberWrapper(msg.author)
                mod_member.xp += 25
            except AttributeError:
                pass

    @Cog.listener()
    async def on_member_update(self, before, after):
        """
        Check if a member has updated roles and modifies them in the database
        """
        if before.roles == after.roles:
            return

        member = MemberWrapper(after)
        if member.exists():
            sub_roles = set()
            for role in after.roles:
                if role.name in ("Prof", "Non Vérifié", "Élève G1", "Élève G2"):
                    member.top_role = role
                elif role.name.startswith("Groupe"):
                    member.group_role = role
                elif role.name != "@everyone":
                    sub_roles.add(role)

            member.sub_roles = sub_roles
        else:
            logging.error(f"The user {after.name} was not found in members table")


def setup(bot):
    bot.add_cog(EventsCog(bot))
