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

from .utils.functions import get_emoji_by_name

logger = logging.getLogger(__name__)


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
        with open(STATIC_DIR / "text/roles.md", encoding="utf-8") as f:
            content = f.read()
            for name in self.reactions:
                if emoji := get_emoji_by_name(ctx.guild, name):
                    content = content.replace(f":{name}:", str(emoji))

            embed = discord.Embed(
                title="Bienvenue!", colour=0xFF22FF, description=content
            )
            embed.set_thumbnail(url=ctx.guild.icon_url)
            embed.set_footer(
                text=f"Généré par {self.bot.user.name} | {datetime.now():%D - %H:%M}"
            )
            message = await ctx.send(embed=embed)

        for name in self.reactions:
            if emoji := get_emoji_by_name(ctx.guild, name):
                await message.add_reaction(str(emoji))
            else:
                logger.error(f"{name} emoji not found")

        database.execute(
            update(GuildModel)
            .where(GuildModel.id == ctx.guild.id)
            .values(message_roles_id=message.id)
        )

    @Cog.listener("on_raw_reaction_add")
    async def on_selection(self, payload):
        """
        Update role from the user selection
        """
        if not hasattr(payload, "guild_id"):
            return  # Ignore DM
        guild = database.execute(
            select(GuildModel).where(GuildModel.id == payload.guild_id)
        ).scalar_one_or_none()
        member = MemberWrapper(payload.member)

        if (
            not guild
            or guild.message_roles_id != payload.message_id
            or member.id == self.bot.user.id
        ):
            return  # Exit if it is not the good message or self reaction

        member = MemberWrapper(payload.member)
        if member.role:
            # remove reaction from the message if member has already a role
            msg = await self.bot.get_channel(payload.channel_id).fetch_message(
                payload.message_id
            )
            await msg.remove_reaction(payload.emoji, member)
            await member.send(
                f"{member.mention} Vous ne pouvez pas re choisir un rôle.\n"
                "Contactez un administrateur si vous avez choisi par erreur."
            )
            return
        try:
            member.role = self.reactions[payload.emoji.name]
            await member.add_roles(member.role)
        except KeyError:
            await member.send(f"{member.mention} Cette réaction est invalide")
        except AttributeError:
            logger.error(f"The user {member.name} was not registered in members table")
        except discord.errors.Forbidden:
            logger.error(
                f"Missing permissions to give the @{member.role.name} "
                f"role to {member.name}"
            )


def setup(bot):
    bot.add_cog(Roles(bot))
