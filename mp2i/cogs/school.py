from typing import List, Optional

import re
import logging

from datetime import datetime
from operator import itemgetter

import discord
from discord.ext.commands import (
    Cog,
    hybrid_command,
    guild_only,
    has_any_role,
)
from discord.app_commands import autocomplete, Choice

from mp2i import STATIC_DIR
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

SCHOOL_REGEX = re.compile(r"^.+[|@] *(?P<prepa>.*)$")

logger = logging.getLogger(__name__)


class School(Cog):
    """
    Interface to manage schools.
    """

    def __init__(self, bot):
        self.bot = bot
        with open(STATIC_DIR / "text/cpge.txt", encoding="UTF-8") as f:
            self.schools = f.read().splitlines()

    async def autocomplete_school(
        self, interaction: discord.Interaction, current: str
    ) -> List[Choice[str]]:
        return [
            Choice(name=choice, value=choice)
            for choice in self.schools
            if current.lower() in choice.lower()
        ]

    @hybrid_command(name="chooseschool")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @autocomplete(school=autocomplete_school)
    async def choose_school(
        self, ctx, school: str, user: Optional[discord.Member] = None
    ):
        """
        Associe un lycée à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        school: Le lycée à associer.
        user: Réservé aux modérateurs
            L'utilisateur à qui on associe le lycée (par défaut, l'auteur de la commande)
        """
        if school not in self.schools and school != "Aucun":
            await ctx.reply("Le nom du lycée n'est pas valide", ephemeral=True)
            return

        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
            if school == "Aucun":
                member.school = None
                response = "Vous ne faites plus partie aucun lycée"
            else:
                member.school = school
                response = f"Vous faites maintenant partie du lycée {school}."

        elif any(r.name in ("Administrateur", "Modérateur") for r in ctx.author.roles):
            member = MemberWrapper(user)
            if school == "Aucun":
                member.school = None
                response = "{user.mention} ne fait plus partie d'un lycée."
            else:
                member.school = school
                response = f"{user.mention} fait maintenant partie du lycée {school}"
        else:
            response = "Vous n'avez pas les droits suffisants."

        await ctx.reply(response, ephemeral=True)

    @hybrid_command(name="members")
    @guild_only()
    async def school_members(self, ctx, school: str):
        """
        Affiche les étudiants d'une école donnée.
        """
        guild = GuildWrapper(ctx.guild)
        members = [
            member for member in guild.members if MemberWrapper(member).school == school
        ]
        if not members:
            await ctx.reply(f"{school} n'a aucun étudiant sur ce serveur.")
            return

        content = ""
        for member in members:
            content += f"- `{member.name}`・{member.mention}\n"

        embed = discord.Embed(
            title=f"Liste des étudiants du lycée {school}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
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
        for member in map(MemberWrapper, guild.members):
            if not member.get_role(referent_role.id):
                continue
            if member.exists() and member.school != "Aucun":
                referents.append((member.name, member.school))

            elif match := SCHOOL_REGEX.match(member.nick):
                referents.append((member.name, match.group(1)))

        content = ""
        for member, school in sorted(referents, key=itemgetter(1)):
            status = guild.get_emoji_by_name(f"{member.status}")
            content += f"- **{school}** : `{member}`・{member.mention} {status}\n"

        embed = discord.Embed(
            title=f"Liste des étudiants référents du serveur {guild.name}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(School(bot))
