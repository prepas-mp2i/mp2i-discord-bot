import re
import logging
from typing import Optional
from operator import attrgetter

import discord
from discord.ext.commands import Cog, Range
from discord.ext.commands import (
    hybrid_command,
    guild_only,
    has_permissions,
    errors,
)


from mp2i.wrappers.guild import GuildWrapper
from mp2i.wrappers.member import MemberWrapper
from mp2i.utils import youtube
from mp2i.utils.discord import defer, has_any_role

logger = logging.getLogger(__name__)

LEADERBOARD_RANK_MAX = 50


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener("on_ready")
    async def set_default_status(self) -> None:
        """
        Initialise le status du bot à /help.
        """
        help_status = "/help"
        await self.bot.change_presence(activity=discord.Game(help_status))

    @hybrid_command(name="resetstatus")
    @guild_only()
    @has_permissions(administrator=True)
    async def reset_status(self, ctx) -> None:
        """
        Réinitialise le status du bot à /help.
        """
        await self.set_default_status()
        await ctx.reply("Status réinitialisé à `/help`.", ephemeral=True)

    @hybrid_command(name="status")
    @guild_only()
    @has_permissions(administrator=True)
    async def change_status(self, ctx, *, query: str) -> None:
        """
        Change le status du bot par une vidéo correspondante à la recherche.

        Parameters
        ----------
        query : str
            Mots clés de la vidéo.
        """
        try:
            video = next(youtube.search(query, n=1))
            activity = discord.Streaming(**video)
            await self.bot.change_presence(activity=activity)
            await ctx.reply("Status changé.", ephemeral=True)

        except StopIteration:
            await ctx.reply("Changement de statut du bot impossible.", ephemeral=True)

        except discord.errors.HTTPException:
            logger.error("Can't change bot presence")

    @hybrid_command(name="clear")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, number: Range[int, 1, 100]) -> None:
        """
        Supprime les n derniers messages du salon.

        Parameters
        ----------
        number : int
            Nombre de messages à supprimer.
        """
        await ctx.channel.purge(limit=int(number) + (ctx.prefix != "/"))
        await ctx.reply(f"{number} messages ont bien été supprimés.", ephemeral=True)

    @clear.error
    async def clear_error(self, ctx, error) -> None:
        """
        Local error handler for clear command.
        """
        if isinstance(error, errors.RangeError):
            msg = f"Le nombre de messages doit être compris entre 1 et {error.maximum}."
        await ctx.reply(msg, ephemeral=True)

    @hybrid_command(name="say")
    @guild_only()
    @has_any_role("Modérateur", "Administrateur")
    async def say(self, ctx, channel: discord.TextChannel, *, message: str) -> None:
        """
        Envoie un message dans un salon.

        Parameters
        ----------
        channel : discord.TextChannel
            Salon où envoyer le message.
        message : str
            Message à envoyer.
        """
        if ctx.prefix == "/":
            await ctx.reply(f"Message envoyé dans {channel.mention}.", ephemeral=True)
        await channel.send(message)

    @hybrid_command(name="profile")
    @guild_only()
    @defer()
    async def profile(self, ctx, member: Optional[discord.Member] = None) -> None:
        """
        Consulte les infos d'un membre.

        Parameters
        ----------
        member : discord.Member
            Membre à consulter.
        """
        member = MemberWrapper(member or ctx.author)
        embed = discord.Embed(title="Profil", colour=int(member.profile_color, 16))
        embed.set_author(name=member.name)
        if member.avatar is None:
            embed.set_thumbnail(url=member.default_avatar.url)
        else:
            embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Pseudo", value=member.mention)
        embed.add_field(name="Membre depuis", value=f"{member.joined_at:%d/%m/%Y}")
        embed.add_field(name="Messages", value=member.messages_count)
        embed.add_field(
            name="Rôles",
            value=" ".join(r.mention for r in member.roles if r.name != "@everyone"),
        )
        if member.high_school:
            embed.add_field(name="CPGE", value=member.high_school)
        if member.generation > 0:
            embed.add_field(name="Génération", value=member.generation)
        if member.engineering_school is not None:
            embed.add_field(name="École d'ingénieur", value=member.engineering_school)

        await ctx.send(embed=embed)

    @hybrid_command(name="profilecolor")
    @guild_only()
    async def change_profile_color(self, ctx, color: str) -> None:
        """Change la couleur de profil.

        Parameters
        ----------
        color : str
            Couleur en hexadécimal.
        """
        member = MemberWrapper(ctx.author)
        hexa_color = color.upper().strip("#")
        if re.match(r"^[0-9A-F]{6}$", hexa_color):
            member.profile_color = color.upper().strip("#")
            await ctx.reply(
                f"Couleur de profil changée en #{hexa_color}.", ephemeral=True
            )
        else:
            await ctx.reply("Format de couleur invalide.", ephemeral=True)

    @hybrid_command(name="servinfos")
    @guild_only()
    async def server_info(self, ctx) -> None:
        """
        Affiche des informations sur les roles du serveur.
        """
        guild = GuildWrapper(ctx.guild)
        embed = discord.Embed(title="Infos du serveur", colour=0xFFA325)
        embed.set_author(name=guild.name)
        embed.set_thumbnail(url=guild.icon.url)
        emoji_people = guild.get_emoji_by_name("silhouettes")
        embed.add_field(name=f"{emoji_people} Membres", value=len(guild.members))

        for role_name, role_cfg in guild.config.roles.items():
            if role_cfg.choice:
                number = len(guild.get_role(role_cfg.id).members)
                emoji = guild.get_emoji_by_name(role_cfg.emoji)
                embed.add_field(name=f"{emoji} {role_name}", value=number)
        await ctx.send(embed=embed)

    @hybrid_command(name="leaderboard")
    @guild_only()
    @defer()
    async def leaderboard(self, ctx, rmax: Optional[int] = 10) -> None:
        """
        Affiche le classement des membres par nombre de messages.

        Parameters
        ----------
        rmax : int
            Rang maximal (compris entre 0 et 50)
        """
        if rmax < 0 or rmax > LEADERBOARD_RANK_MAX:
            message = f"rmax doit être compris entre 0 et {LEADERBOARD_RANK_MAX}"
            return await ctx.reply(message, ephemeral=True)

        members = [MemberWrapper(m) for m in ctx.guild.members if not m.bot]
        members.sort(key=attrgetter("messages_count"), reverse=True)

        author = MemberWrapper(ctx.author)
        rank = members.index(author) + 1
        content = f"→ {rank}. **{author.name}** : {author.messages_count} messages\n\n"

        if rmax == 0:
            title = "Votre classement dans le serveur :"
        else:
            title = f"Top {rmax} des membres du serveur"

        for r, member in enumerate(members[:rmax], 1):
            content += f"{r}. **{member.name}** : {member.messages_count} messages\n"

        embed = discord.Embed(colour=0x2BFAFA, title=title, description=content)
        await ctx.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Commands(bot))
