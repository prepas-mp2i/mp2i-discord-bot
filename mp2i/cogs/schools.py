from typing import List, Optional

import re
import logging

from datetime import datetime
from operator import itemgetter

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, Range
from discord.app_commands import autocomplete, Choice, choices

from mp2i import STATIC_DIR
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper
from mp2i.utils.discord import defer, has_any_role

SCHOOL_REGEX = re.compile(r"^.+[|@] *(?P<prepa>.*)$")

logger = logging.getLogger(__name__)


class School(Cog):
    """
    Interface to manage schools.
    """

    def __init__(self, bot):
        self.bot = bot
        with open(STATIC_DIR / "text/cpge.txt") as f:
            self.high_schools = f.read().splitlines()
        with open(STATIC_DIR / "text/engineering.txt") as f:
            self.engineering_schools = f.read().splitlines()

    async def autocomplete_school(
        self, interaction: discord.Interaction, current: str
    ) -> List[Choice[str]]:
        """
        Return a list of school corresponding to current text.
        """
        await interaction.response.defer()  # Defer the response to avoid timeout

        type = interaction.namespace.type
        if type == "cpge":
            schools = self.high_schools
        elif type == "engineering":
            schools = self.engineering_schools
        else:
            schools = []

        filtered_schools = [s for s in schools if current.lower().strip() in s.lower()]
        return [Choice(name=s, value=s) for s in filtered_schools[:20]]

    @hybrid_command(name="school")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Intégré", "Modérateur", "Administrateur")
    @autocomplete(school=autocomplete_school)
    @choices(
        type=[
            Choice(name="CPGE", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    async def school_selection(
        self, ctx, type: str, school: str, user: Optional[discord.Member] = None
    ):
        """
        Associe une CPGE ou une école à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        type : CPGE ou École d'ingénieur
        school: Le nom de l'école à associer.
        user: Réservé aux Administrateurs et Modérateurs
            L'utilisateur à qui on associe l'école (par défaut, l'auteur de la commande)
        """
        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
        elif ctx.author.guild_permissions.manage_roles:
            member = MemberWrapper(user)
        else:
            await ctx.reply("Vous n'avez pas les droits suffisants.", ephemeral=True)
            return

        if type == "cpge":
            if school == "Aucun":
                response = f"{member.name} ne fait plus partie d'une CPGE."
                member.high_school = None
            elif school in self.high_schools:
                response = f"{member.name} fait maintenant partie du lycée {school}."
                member.high_school = school
            else:
                response = f"Le lycée {school} n'existe pas."
        elif type == "engineering":
            if school == "Aucun":
                response = f"{member.name} ne fait plus partie d'aucune école."
                member.engineering_school = None
            elif school in self.engineering_schools:
                response = f"{member.name} fait maintenant partie de l'école {school}."
                member.engineering_school = school
            else:
                response = f"L'école {school} n'existe pas"
        else:
            response = "Veuillez choisir un type entre `cpge` et `engineering`."

        await ctx.reply(response, ephemeral=True)

    @hybrid_command(name="generation")
    @has_any_role("MP2I", "MPI", "Ex MPI", "Intégré", "Modérateur", "Administrateur")
    @guild_only()
    async def generation(
        self,
        ctx,
        year: Range[int, 2021, datetime.now().year],
        user: Optional[discord.Member] = None,
    ):
        """
        Définit l'année d'arrivée en sup

        Parameters
        ----------
        year: L'année d'arrivée en sup
        user: Réservé aux modérateurs
            L'utilisateur à qui on associe la date (par défaut, l'auteur de la commande)
        """
        member = MemberWrapper(ctx.author)
        if user is None or user == ctx.author:
            member.generation = year
            await ctx.reply(
                f"Vous faites maintenant partie de la génération {year} !",
                ephemeral=True,
            )
        elif member.guild_permissions.manage_roles:
            member.generation = year
            await ctx.reply(
                f"{user.mention} fait maintenant partie de la génération {year} !",
                ephemeral=True,
            )
        else:
            await ctx.reply("Vous n'avez pas les droits suffisants.", ephemeral=True)

    @hybrid_command(name="members")
    @guild_only()
    @autocomplete(school=autocomplete_school)
    @choices(
        type=[
            Choice(name="CPGE", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    @defer(ephemeral=False)
    async def members(self, ctx, type: str, school: str):
        """
        Affiche les étudiants d'une école donnée.
        """
        guild = GuildWrapper(ctx.guild)
        members = [m for m in map(MemberWrapper, guild.members) if m.exists()]
        if type == "cpge":
            students = [m for m in members if m.high_school == school]
            referent_role = guild.get_role_by_qualifier("Référent CPGE")
        elif type == "engineering":
            students = [m for m in members if m.engineering_school == school]
            referent_role = guild.get_role_by_qualifier("Référent École")
        else:
            await ctx.reply("Précisez un type entre `cpge` ou `engineering`.")
            return

        if not students:
            await ctx.reply(f"{school} n'a aucun étudiant sur {guild.name}.")
            return
        referents = [m for m in students if m.get_role(referent_role.id)]

        content = f"Nombre d'étudiants : {len(students)}\n"
        for referent in referents:
            status = guild.get_emoji_by_name(f"{referent.status}")
            content += f"Référent : `{referent.name}`・{referent.mention} {status}\n\n"
        for member in students:
            content += f"- `{member.name}`・{member.mention}\n"

        embed = discord.Embed(
            title=f"Liste des étudiants à {school}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
        await ctx.reply(embed=embed)

    @hybrid_command(name="referents")
    @guild_only()
    @choices(
        type=[
            Choice(name="CPGE", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    @defer()
    async def referents(self, ctx, type: Optional[str] = "cpge") -> None:
        """
        Liste les étudiants référents du serveur.
        """
        guild = GuildWrapper(ctx.guild)
        referent_role = guild.get_role_by_qualifier("Référent CPGE")

        if type == "engineering":
            referent_role = guild.get_role_by_qualifier("Référent École")
        else:
            referent_role = guild.get_role_by_qualifier("Référent CPGE")
        if referent_role is None:
            raise ValueError("Corresponding referent role is not in bot config file.")

        referents = []
        for member in map(MemberWrapper, guild.members):
            if not member.get_role(referent_role.id):
                continue
            if type == "cpge" and member.exists() and member.high_school is not None:
                referents.append((member, member.high_school))
            elif type == "engineering" and member.exists() and member.engineering_school is not None:
                referents.append((member, member.engineering_school))
            elif match := SCHOOL_REGEX.match(member.nick):
                referents.append((member, match.group(1)))

        content = ""
        for member, school in sorted(referents, key=itemgetter(1)):
            status = guild.get_emoji_by_name(f"{member.status}")
            content += f"- **{school}** : `{member.name}`・{member.mention} {status}\n"

        embed = discord.Embed(
            title=f"Liste des {referent_role.name} du serveur {guild.name}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(School(bot))
