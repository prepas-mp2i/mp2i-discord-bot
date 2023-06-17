from datetime import datetime

import discord
from discord.ext.commands import Cog, command, is_owner, guild_only
from sqlalchemy import insert

from mp2i import STATIC_DIR
from mp2i.models import SuggestionModel
from mp2i.utils import database
from mp2i.wrappers.guild import GuildWrapper


class Suggestion(Cog):
    """
    Offers commands to allow members to propose suggestions and interact with them
    """

    MINIMUM_PINS = 5

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
        Send the rules to suggestion channel.
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
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Généré par {self.bot.user.name}")
        await ctx.send(embed=embed)

    @Cog.listener("on_message")
    async def make_suggestion(self, msg) -> None:
        if msg.author.bot or not self.is_suggestion_channel(msg.channel):
            return
        try:
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            await msg.channel.create_thread(
                name=f"Suggestion de {msg.author.name}", message=msg
            )
        except discord.errors.NotFound:
            pass

    @Cog.listener("on_raw_reaction_add")
    async def close_suggestion(self, payload) -> None:
        """
        Send result to all users when an admin add a reaction.
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

        accept = discord.utils.get(suggestion.reactions, emoji="✅")
        decline = discord.utils.get(suggestion.reactions, emoji="❌")
        citation = (
            "\n> ".join(suggestion.content.split("\n"))
            + f"\n\n✅: {accept.count-1} vote(s), ❌: {decline.count-1} vote(s)"
        )
        if accepted := str(payload.emoji) == accept.emoji:
            database.execute(
                insert(SuggestionModel).values(
                    author_id=suggestion.author.id,
                    date=datetime.now(),
                    description=suggestion.content,
                )
            )
            citation += ("\n__Note__: Il faut parfois attendre plusieurs jours"
                         " avant qu'elle soit effective")  # fmt: skip

        embed = discord.Embed(
            colour=0xFF22BB,
            title=f"Suggestion {'acceptée' if accepted else 'refusée'}",
            description=f"> {citation}",
        )
        file = discord.File(STATIC_DIR / "img/alert.png")
        embed.set_thumbnail(url="attachment://alert.png")
        embed.set_author(name=suggestion.author.name)

        await channel.send(file=file, embed=embed)
        await suggestion.delete()

    @Cog.listener("on_raw_reaction_add")
    @guild_only()
    async def add_pin(self, payload) -> None:
        """
        Add a pin to a message and send it to website channel when
        it reach the required number of pins reactions.
        """
        print(str(payload.emoji))
        if str(payload.emoji) != "📌":
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        pins = discord.utils.get(message.reactions, emoji="📌")
        if pins.count < self.MINIMUM_PINS:
            return

        author = message.author
        embed = discord.Embed(
            colour=0x00FF00,
            title="Message épinglé",
            description="Un message a été retenu par la communauté, vous pouvez "
            "probablement l'ajouter dans la [FAQ](https://prepas-mp2i.fr/faq/).",
            timestamp=datetime.now(),
        )
        embed.add_field(name="Lien du message", value=message.jump_url)
        embed.set_author(name=author.name, icon_url=author.avatar.url)
        embed.set_footer(text=self.bot.user.name)
        website_chan = self.bot.get_channel(
            GuildWrapper(channel.guild).config.channels.website
        )
        await website_chan.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Suggestion(bot))
