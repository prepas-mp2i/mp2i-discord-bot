import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog, command, is_owner

from mp2i import STATIC_DIR
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

logger = logging.getLogger(__name__)


class Roles(Cog):
    """
    Offers an interface to manage roles and send messages
    to choice his roles inside the guild
    """

    def __init__(self, bot):
        self.bot = bot

    @command(name="roles_selection", hidden=True)
    @is_owner()
    async def send_selection(self, ctx) -> None:
        """
        Generate a message to select a role in order to manage permissions
        """
        guild = GuildWrapper(ctx.guild)

        with open(STATIC_DIR / "text/roles.md", encoding="utf-8") as f:
            content = f.read()
            for role in guild.config.roles.values():
                if emoji := guild.get_emoji_by_name(role.emoji):
                    content = content.replace(f"({role.name})", str(emoji))

            embed = discord.Embed(
                title="Bienvenue sur le serveur des prépas MP2I/MPI !",
                colour=0xFF22FF,
                description=content,
                timestamp=datetime.now(),
            )
            embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text=self.bot.user.name)
            message = await ctx.send(embed=embed)

        for role in guild.config.roles.values():
            if (emoji := guild.get_emoji_by_name(role.emoji)) and role.emoji != "Prof":
                await message.add_reaction(emoji)
            else:
                logger.error(f"{role.emoji} emoji not found")

        guild.roles_message_id = message.id
        await ctx.message.delete()

    @Cog.listener("on_raw_reaction_add")
    async def on_selection(self, payload) -> None:
        """
        Update role from the user selection
        """
        if not hasattr(payload, "guild_id") or payload.member.id == self.bot.user.id:
            return  # Ignore DM and bot reaction

        guild = GuildWrapper(self.bot.get_guild(payload.guild_id))
        if guild.roles_message_id != payload.message_id:
            return  # Ignore if it is not the good message

        member = MemberWrapper(payload.member)
        emoji_role = guild.get_role_by_emoji_name(payload.emoji.name)
        if emoji_role is None:
            await member.send("Cette réaction est invalide")
            return  # This emoji is not mapped to an authorized role
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            # Remove all other member's reaction from the message
            for role in guild.config.roles.values():
                if (emoji := guild.get_emoji_by_name(role.emoji)) != payload.emoji:
                    await message.remove_reaction(emoji, member)
            # Remove all member's config roles
            await member.remove_roles(*map(guild.get_role, guild.config.roles))
            member.update(role=emoji_role.name)
            await member.add_roles(member.role)  # Add the new role from the database

        except discord.errors.Forbidden as err:
            logger.error(err)


async def setup(bot) -> None:
    await bot.add_cog(Roles(bot))
