from __future__ import annotations

import json
import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog, command, is_owner
from sqlalchemy import select, update

from mp2i import STATIC_DIR
from mp2i.models import GuildModel
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper

from .utils import get_role_by_name


class Roles(Cog):
    """
    Offers an interface to manage roles and send messages
    to choice his roles inside the guild
    """

    def __init__(self, bot):
        self.bot = bot

        with open(STATIC_DIR / "json/reactions.json", encoding="utf-8") as f:
            self.reactions = json.load(f)

    @command(name="roles_selection", hidden=True)
    @is_owner()
    async def send_selection(self, ctx):
        """
        Generate a message to select a role in order to manage permissions
        """
        await ctx.message.delete()

        with open(STATIC_DIR / "text/roles.md", encoding="utf-8") as content:
            embed = discord.Embed(
                title="Bienvenue!", colour=0xFF22FF, description=content.read()
            )
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.set_footer(
                text=f"Généré par {self.bot.user.name} | {datetime.now():%D - %H:%M}"
            )
            message = await ctx.send(embed=embed)

        for reaction in self.reactions:
            await message.add_reaction(reaction)

        database.execute(
            update(GuildModel)
            .where(GuildModel.id == ctx.guild.id)
            .values(message_roles_id=message.id)
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_selection(self, payload):
        """
        Update role or send a DM message to the user to choice his sub roles
        """
        if not hasattr(payload, "guild_id"):
            return  # guild only

        guild_model = database.execute(
            select(GuildModel).where(GuildModel.id == payload.guild_id)
        ).scalar_one_or_none()

        if guild_model and guild_model.message_roles_id != payload.message_id:
            return  # Exit if it's not for the message to choice roles

        member = MemberWrapper(payload.member)
        try:
            await member.remove_roles(member.role)
            member.role = get_role_by_name(
                member.guild, self.reactions[payload.emoji.name]
            )
            await member.add_roles(member.role)
        except KeyError:
            await member.dm_channel.send(
                f"{member.mention} Cette réaction est invalide"
            )
        except AttributeError:
            logging.error(f"The user {member.name} was not registered in members table")


def setup(bot):
    bot.add_cog(Roles(bot))
