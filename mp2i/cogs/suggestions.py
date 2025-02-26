from datetime import datetime

import discord
from discord.ext.commands import Cog, hybrid_command, is_owner, guild_only
from discord.app_commands import Choice, choices
from sqlalchemy import insert, select, update

from mp2i import STATIC_DIR
from mp2i.models import SuggestionModel
from mp2i.utils import database
from mp2i.wrappers.guild import GuildWrapper
from mp2i.utils.discord import defer

class Suggestion(Cog):
    """
    Offers commands to allow members to propose suggestions and interact with them
    """

    MINIMUM_PINS = 5

    def __init__(self, bot):
        self.bot = bot

    @hybrid_command(name="suggestionsrules")
    @is_owner()
    async def send_suggestions_rules(self, ctx) -> None:
        """
        Affiche le fonctionnement des suggestions.
        """
        guild = GuildWrapper(ctx.guild)
        if ctx.channel != guild.suggestion_channel:
            return

        with open(STATIC_DIR / "text/suggestions.md", encoding="utf-8") as f:
            content = f.read()
        embed = discord.Embed(
            title="Fonctionnement des suggestions",
            description=content,
            colour=0xFF66FF,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Généré par {self.bot.user.name}")
        await ctx.send(embed=embed)

    @Cog.listener("on_message")
    async def make_suggestion(self, msg) -> None:
        """
        Add reactions to a suggestion message and create a thread.
        """
        if msg.author.bot or isinstance(msg.channel, discord.DMChannel):
            return
        if msg.channel != GuildWrapper(msg.channel.guild).suggestion_channel:
            return
        try:
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            await msg.channel.create_thread(
                name=f"Suggestion de {msg.author.name}", message=msg
            )
        except discord.errors.NotFound:
            pass
        database.execute(
            insert(SuggestionModel).values(
                author_id=msg.author.id,
                date=datetime.now(),
                guild_id=msg.guild.id,
                description=msg.content,
                message_id=msg.id,
                state="open",
            )
        )

    @Cog.listener("on_raw_reaction_add")
    async def close_suggestion(self, payload) -> None:
        """
        Send result to all users when an admin add a reaction.
        """
        if payload.member.bot or str(payload.emoji) not in ("✅", "❌", "🔒"):
            return
        try:
            channel = self.bot.get_channel(payload.channel_id)
            suggestion = await channel.fetch_message(payload.message_id)
        except discord.errors.NotFound:
            return
        if channel != GuildWrapper(channel.guild).suggestion_channel:
            return
        if not payload.member.guild_permissions.administrator:
            return  # only administrator can close a suggestion
        accept = discord.utils.get(suggestion.reactions, emoji="✅")
        decline = discord.utils.get(suggestion.reactions, emoji="❌")
        close = discord.utils.get(suggestion.reactions, emoji="🔒")
        citation = (
            "\n> ".join(suggestion.content.split("\n"))
            + f"\n\n✅: {accept.count-1} vote(s), ❌: {decline.count-1} vote(s)"
        ) 
        accepted = str(payload.emoji) == accept.emoji
        declined = str(payload.emoji) == decline.emoji
        database.execute(
            update(SuggestionModel)
            .where(SuggestionModel.message_id == suggestion.id)
            .values(
                state="accepted" if accepted else "declined" if declined else "closed",
                date=datetime.now()
            )
        )
        if accepted:
            embed = discord.Embed(colour=0x77B255, title=f"Suggestion acceptée", description=f"> {citation}\n_**Note**: Il faut parfois attendre plusieurs jours avant qu'elle soit effective_")
        elif declined:
            embed = discord.Embed(colour=0xDD2E44, title=f"Suggestion refusée", description=f"> {citation}")
        else:
            embed = discord.Embed(colour=0xA9A6A7, title=f"Suggestion fermée", description=f"> {citation}")
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
        if str(payload.emoji) != "📌":
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        pins = discord.utils.get(message.reactions, emoji="📌", me=False)
        if pins is None or pins.count < self.MINIMUM_PINS:
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
        # Pour ne pas envoyer le message plusieurs fois
        await message.add_reaction("📌")
    
    @hybrid_command(name="suggestions")
    @guild_only()
    @defer()
    @choices(
        state=[
            Choice(name="En cours", value="open"),
            Choice(name="Acceptées", value="accepted"),
            Choice(name="Refusées", value="declined"),
            Choice(name="Fermées", value="closed"),
        ]
    )
    async def suggestions(self, ctx, state: str) -> None:
        """
        Affiche les suggestions

        Parameters
        ----------
        state : str
            Le type de suggestions à afficher : En cours/Acceptées/Refusées/Fermées
        """
        suggestions = database.execute(
            select(SuggestionModel)
            .where(
            SuggestionModel.state == state,
            SuggestionModel.guild_id == ctx.guild.id
            )
            .order_by(SuggestionModel.date.desc())
            .limit(10)
        ).scalars().all()

        if not suggestions:
            await ctx.reply("Aucune suggestion trouvée pour cet état.", ephemeral=True)
            return

        if state == "accepted":
            embed = discord.Embed(title=f"Suggestions acceptées", colour=0x77B255, timestamp=datetime.now())
        elif state == "declined":
            embed = discord.Embed(title=f"Suggestions refusées", colour=0xDD2E44, timestamp=datetime.now())
        elif state == "closed":
            embed = discord.Embed(title=f"Suggestions fermées", colour=0xA9A6A7, timestamp=datetime.now())
        else:
            embed = discord.Embed(title=f"Suggestions en cours", colour=0xA9A6A7, timestamp=datetime.now())

        for i, suggestion in enumerate(suggestions):
            user = ctx.guild.get_member(suggestion.author_id)
            
            if state == "open":
                message = await GuildWrapper(ctx.guild).suggestion_channel.fetch_message(suggestion.message_id)
                embed.add_field(
                    name=f"{i+1} - Suggestion de {user.name if user else 'Utilisateur inconnu'} le {suggestion.date:%d/%m/%Y}",
                    value=message.jump_url,
                    inline=False,
                )
            else:
                description_embed = suggestion.description.replace("\n", "\n> ")
                embed.add_field(
                    name=f"{i+1} - Suggestion de {user.name if user else 'Utilisateur inconnu'} le {suggestion.date:%d/%m/%Y}",
                    value=f"> {description_embed}",
                    inline=False,
                )

        await ctx.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Suggestion(bot))
