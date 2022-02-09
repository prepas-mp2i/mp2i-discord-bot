from datetime import datetime

import discord
from discord.ext.commands import Cog, command, is_owner
from sqlalchemy import insert

from mp2i import STATIC_DIR
from mp2i.models import SuggestionModel
from mp2i.utils import database
from mp2i.wrappers.guild import GuildWrapper


class Suggestion(Cog):
    """
    Offers commands to allow members to propose suggestions and interact with them
    """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def is_suggestion_channel(chan: discord.TextChannel) -> bool:
        if isinstance(chan, discord.DMChannel):
            return False
        return GuildWrapper(chan.guild).config.channels.suggestion == chan.id

    @command(name="suggestions_rules", hidden=True)
    @is_owner()
    async def send_suggestions_rules(self, ctx) -> None:
        """
        Send the rules for suggestion channel
        """
        if not self.is_suggestion_channel(ctx.channel):
            return

        await ctx.message.delete()
        with open(STATIC_DIR / "text/suggestions.md", encoding="utf-8") as f:
            content = f.read()
        embed = discord.Embed(
            title="Fonctionnement des suggestions",
            description=content,
            colour=0xFF66FF,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.set_footer(text=f"Généré par {self.bot.user.name}")
        await ctx.send(embed=embed)

    @Cog.listener("on_message")
    async def make_suggestion(self, message) -> None:
        if not self.is_suggestion_channel(message.channel):
            return
        try:
            await message.add_reaction("✅")
            await message.add_reaction("❌")
        except discord.errors.NotFound:
            pass

    @Cog.listener("on_raw_reaction_add")
    async def close_suggestion(self, payload) -> None:
        """
        Send result to all users when an admin add a reaction
        """
        if str(payload.emoji) not in ("✅", "❌"):
            return
        try:
            channel = self.bot.get_channel(payload.channel_id)
            suggestion = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return
        if not self.is_suggestion_channel(channel):
            return
        if not await self.bot.is_owner(payload.member):
            return  # only owner can close a suggestion

        if accepted := str(payload.emoji) == "✅":
            database.execute(
                insert(SuggestionModel).values(
                    author_id=suggestion.author.id,
                    date=datetime.now(),
                    description=suggestion.content,
                )
            )
        citation = "\n> ".join(suggestion.content.split("\n"))
        embed = discord.Embed(
            colour=0xFF22BB,
            title=f"Suggestion {'acceptée' if accepted else 'refusée'}",
            description=f"{citation} \n"
            "__Note__: \n Il faut parfois attendre plusieurs jours "
            "avant qu'elle soit effective",
        )
        file = discord.File(STATIC_DIR / "img/alert.png")
        embed.set_thumbnail(url="attachment://alert.png")
        embed.set_author(name=suggestion.author.name)

        await channel.send(file=file, embed=embed)
        await suggestion.delete()


def setup(bot) -> None:
    bot.add_cog(Suggestion(bot))
