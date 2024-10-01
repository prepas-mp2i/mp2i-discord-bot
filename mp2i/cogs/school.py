from typing import List, Optional

import re
import logging

from datetime import datetime
from operator import itemgetter

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_any_role
from discord.app_commands import autocomplete, Choice, choices, Range

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
        with open(STATIC_DIR / "text/cpge.txt") as f:
            self.high_schools = f.read().splitlines()
        with open(STATIC_DIR / "text/engineering.txt") as f:
            self.engineering_schools = f.read().splitlines()

    async def autocomplete_school(
        self, interaction: discord.Interaction, current: str
    ) -> List[Choice[str]]:
        type = interaction.namespace.type
        if type == "cpge":
            schools = self.high_schools
        else:
            schools = self.engineering_schools
        return [
            Choice(name=choice, value=choice)
            for choice in schools
            if current.lower() in choice.lower()
        ]

    @hybrid_command(name="school")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Intégré", "Moderateur", "Administrateur")
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
        type : CPGE ou école d'ingénieur
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
        else:
            if school == "Aucun":
                response = f"{member.name} ne fait plus partie d'aucune école."
                member.engineering_school = None
            elif school in self.engineering_schools:
                response = f"{member.name} fait maintenant partie de l'école {school}."
                member.engineering_school = school
            else:
                response = f"L'école {school} n'existe pas"

        await ctx.reply(response, ephemeral=True)

    @hybrid_command(name="generation")
    @has_any_role("MP2I", "MPI", "Ex MPI", "Intégré", "Moderateur", "Administrateur")
    @guild_only()
    async def generation(
        self,
        ctx,
        gen: Range[int, 2021, datetime.now().year],
        user: Optional[discord.Member] = None,
    ):
        """
        Définit l'année d'arrivée en sup

        Parameters
        ----------
        gen: L'année d'arrivée en sup
        user: Réservé aux modérateurs
            L'utilisateur à qui on associe la date (par défaut, l'auteur de la commande)
        """
        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
            member.generation = gen
            await ctx.reply(
                f"Vous faites maintenant partie de la génération {gen} !",
                ephemeral=True,
            )
        elif any(r.name in ("Administrateur", "Modérateur") for r in ctx.author.roles):
            member = MemberWrapper(user)
            member.generation = gen
            await ctx.reply(
                f"{user.mention} fait maintenant partie de la génération {gen} !",
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
    async def school_members(self, ctx, type: str, school: str):
        """
        Affiche les étudiants d'une école donnée.
        """
        guild = GuildWrapper(ctx.guild)
        members = [m for m in map(MemberWrapper, guild.members) if m.exists()]
        if type == "cpge":
            students = [m for m in members if m.high_school == school]
        else:
            students = [m for m in members if m.engineering_school == school]

        if not students:
            await ctx.reply(f"{school} n'a aucun étudiant sur ce serveur.")
            return

        content = f"Nombre d'étudiants : {len(students)}\n"
        for member in students:
            content += f"- `{member.name}`・{member.mention}\n"
        if type == "cpge":
            title = f"Liste des étudiants de la CPGE {school}"
        else:
            title = f"Liste des étudiants à {school}"
        embed = discord.Embed(
            title=title,
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name)
        await ctx.reply(embed=embed)

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
            if member.exists() and member.high_school is not None:
                referents.append((member, member.high_school))
            elif match := SCHOOL_REGEX.match(member.nick):
                referents.append((member, match.group(1)))

        content = ""
        for member, school in sorted(referents, key=itemgetter(1)):
            status = guild.get_emoji_by_name(f"{member.status}")
            content += f"- **{school}** : `{member.name}`・{member.mention} {status}\n"

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
