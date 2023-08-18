import re
import logging
from typing import Optional
from datetime import datetime
from operator import itemgetter

from sqlalchemy import insert, select
import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_permissions
from mp2i.models import MemberModel

from mp2i.wrappers.guild import GuildWrapper
from mp2i.wrappers.member import MemberWrapper

from mp2i.utils import database, youtube

logger = logging.getLogger(__name__)

PREPA_REGEX = re.compile(r"^.+[|@] *(?P<prepa>.*)$")


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
    async def clear(self, ctx, number: int = 1) -> None:
        """
        Supprime les n derniers messages du salon

        Parameters
        ----------
        number : int
            Nombre de messages à supprimer.
        """
        await ctx.channel.purge(limit=int(number))
        await ctx.reply(f"{number} messages ont bien été supprimés.", ephemeral=True)

    @hybrid_command(name="say")
    @guild_only()
    @has_permissions(manage_messages=True)
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
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Pseudo", value=member.mention)
        embed.add_field(name="Membre depuis", value=f"{member.joined_at:%d/%m/%Y}")
        embed.add_field(name="Messages", value=member.messages_count)
        embed.add_field(
            name="Rôles",
            value=" ".join(r.mention for r in member.roles if r.name != "@everyone"),
        )
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

    @hybrid_command(name="referents")
    @guild_only()
    async def referents(self, ctx) -> None:
        """
        Liste les étudiants référents du serveur.
        """
        guild = GuildWrapper(ctx.guild)
        referent_role = guild.get_role_by_qualifier("Référent")
        if referent_role is None:
            await logger.warning("No referent role in bot config file.")

        referents = []
        for member in guild.members:
            if not member.get_role(referent_role.id):
                continue
            if match := PREPA_REGEX.match(member.nick):
                referents.append((member, match.group(1)))

        content = ""
        for member, prepa in sorted(referents, key=itemgetter(1)):
            status = guild.get_emoji_by_name(f"{member.status}")
            content += f"- **{prepa}** : `{str(member)}`・{member.mention} {status}\n"

        embed = discord.Embed(
            title=f"Liste des étudiants référents du serveur {guild.name}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
        await ctx.send(embed=embed)

    @hybrid_command(name="leaderboard")
    async def leaderboard(self, ctx, rmax: Optional[int] = 10):
        """
        Affiche le classement des membres par nombre de messages.

        Parameters
        ----------
        rmax : int
            Rang maximal.
        """
        members = [MemberWrapper(m) for m in ctx.guild.members if not m.bot]
        author = MemberWrapper(ctx.author)
        rank = members.index(author) + 1

        content = f"→ {rank}. **{author.name}** : {author.messages_count} messages\n\n"
        for r, member in enumerate(members[:rmax], 1):
            content += f"{r}. **{member.name}** : {member.messages_count} messages\n"
        
        embed = discord.Embed(
            colour=0x2BFAFA, 
            title=f"Top {rmax} des membres du serveur",
            description=content
        )
        await ctx.send(embed=embed)

    @Cog.listener("on_message")
    async def unbinarize(self, msg: discord.Message):
        """
        Vérifie si le message est un texte binaire et le convertit en ASCII.
        """
        if not re.fullmatch(r"([01]{8}\s?)+", msg.content):
            return
        await msg.channel.send(
            f"{msg.author.mention}: "
            + "".join(chr(int(b, 2)) for b in re.findall("[01]{8}", msg.content))
        )


async def setup(bot) -> None:
    await bot.add_cog(Commands(bot))
