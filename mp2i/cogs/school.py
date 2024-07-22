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
from discord import app_commands

from typing import List, Optional

from mp2i import STATIC_DIR
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

from collections import Counter

PREPA_REGEX = re.compile(r"^.+[|@] *(?P<prepa>.*)$")

logger = logging.getLogger(__name__)


class School(Cog):
    """
    Association d'un membre et d'un lycée
    """

    def __init__(self, bot):
        self.bot = bot
        with open(STATIC_DIR / "text/Liste_lycee_MP2I.txt", encoding="UTF-8") as f:
            self.schools = f.read().splitlines()

    async def autocomplete_school(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in self.schools
            if current.lower() in choice.lower()
        ]

    @hybrid_command(name="chooseschool")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @app_commands.autocomplete(school=autocomplete_school)
    async def choose_school(
        self, ctx, school: str, user: Optional[discord.Member] = None
    ):
        """
        Associe un lycée à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        school : str
            Le lycée à associer
        user : Optional[discord.Member]
            Réservé aux modérateurs
            L'utilisateur à qui on associe le lycéee (avec soi-même l'argument est vide)
        """
        if not school in self.schools and school != "Aucun":
            await ctx.reply("Le nom du lycée n'est pas valide", ephemeral=True)
            return
        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
            if school == "Aucun":
                member.school = None
                await ctx.reply(
                    "Vous ne faites plus partie aucun lycée", ephemeral=True
                )
            else:
                member.school = school
                await ctx.reply(
                    f"Vous faites maintenant partie du lycée {school}", ephemeral=True
                )
        else:
            if any(
                r in ctx.author.roles
                for r in [
                    GuildWrapper(ctx.guild).get_role_by_qualifier("Modérateur"),
                    GuildWrapper(ctx.guild).get_role_by_qualifier("Administrateur"),
                ]
            ):
                member = MemberWrapper(user)
                if school == "Aucun":
                    member.school = None
                    await ctx.reply(
                        "{user.mention} ne fait plus partie aucun lycée", ephemeral=True
                    )
                else:
                    member.school = school
                    await ctx.reply(
                        f"{user.mention} fait maintenant partie du lycée {school}",
                        ephemeral=True,
                    )
            else:
                await ctx.reply(
                    f"Vous n'avez pas les droits suffisants pour modifier le lycée d'autres personnes",
                    ephemeral=True,
                )

    @hybrid_command(name="schools")
    @guild_only()
    async def schools(self, ctx):
        """
        Affiche le nombre de étudiants étant ou ayant été en MP2I/MPI réparti par lycée
        """
        school_members = map(lambda m: MemberWrapper(m).school, ctx.guild.members)
        school_count = Counter(school_members)
        content = ""
        for school, nb_student in school_count.items():
            plural = "s" if nb_student > 1 else ""
            if nb_student > 0 and school != "Aucun":
                content += f"**{school}** : {nb_student} étudiant{plural}\n"
        title = "Nombre de membres du serveur par lycée"
        embed = discord.Embed(
            colour=0x2BFAFA,
            title=title,
            description=content,
        )
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
            member_db = MemberWrapper(member)
            if member_db.exists() and member_db.school != "Aucun":
                referents.append((member, member_db.school))
            elif match := PREPA_REGEX.match(member.nick):
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


async def setup(bot) -> None:
    await bot.add_cog(School(bot))
