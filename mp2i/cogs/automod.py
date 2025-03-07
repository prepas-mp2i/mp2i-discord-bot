import re
import json
import logging
from datetime import datetime

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only

from mp2i import STATIC_DIR, MODEL_DIR
from mp2i.utils.discord import has_any_role
from mp2i.utils.classifier import ToxicityClassifier
from mp2i.wrappers.guild import GuildWrapper
from mp2i.wrappers.member import MemberWrapper

logger = logging.getLogger(__name__)


class Automod(Cog):
    XLM_ROBERTA_MODEL = "multilingual-toxic-xlm-roberta"

    def __init__(self, bot):
        self.bot = bot
        self.classifier = ToxicityClassifier(MODEL_DIR / self.XLM_ROBERTA_MODEL)
        self.exceptions = self._load_exceptions()

    def _load_exceptions(self) -> dict:
        with open(STATIC_DIR / "text/exceptions.json") as f:
            return json.load(f)

    def is_toxic(self, msg: discord.Message) -> bool:
        """
        Check if a message is toxic or not.
        """
        for exc in self.exceptions:
            msg.content = re.sub(exc, self.exceptions[exc], msg.content)

        return self.classifier.predict(msg.content, threshold=0.75)

    @Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """
        Log message in database and update message count
        """
        if msg.author.bot:
            return  # Ignore bot messages
        if self.is_toxic(msg):
            return await self.moderate(msg)

        member = MemberWrapper(msg.author)
        if member.exists():
            member.messages_count += 1

    @Cog.listener()
    async def on_message_edit(self, before, after) -> None:
        """
        When a message is edited, send logs in the log channel
        """
        guild = GuildWrapper(before.guild)
        if not before.guild or not (log_chan := guild.log_channel):
            return logging.warning("No log channel set")

        if before.channel == guild.admin_channel or before.author.bot:
            return  # Ignore bot and admin channel

        if self.is_toxic(after):
            return await self.moderate(before)

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

    @staticmethod
    async def moderate(msg: discord.Message) -> None:
        """
        Moderates a message by deleting it and sending logs.
        """
        await msg.delete()  # Will trigger on_message_delete event
        embed = discord.Embed(
            title="Message modéré pour contenu inapproprié",
            description=f">>> {msg.content}",
            colour=0xFFA325,
        )
        guild = GuildWrapper(msg.guild)
        await guild.log_channel.send(embed=embed)
        await msg.author.send(
            f"Votre message a été modéré pour contenu inapproprié :\n>>> {msg.content}"
        )

    @has_any_role("Modérateur", "Administrateur")
    @guild_only()
    @hybrid_command(name="exception")
    async def add_exception(self, ctx, pattern: str, replacement: str) -> None:
        """
        Add a pattern to the exceptions dictionary.
        """
        self.exceptions[pattern] = replacement
        with open(STATIC_DIR / "text/exceptions.json", "w") as f:
            json.dump(self.exceptions, f, indent=2)

        await ctx.reply(f"Règle `{pattern} -> {replacement}` ajoutée avec succès.")


async def setup(bot):
    await bot.add_cog(Automod(bot))
