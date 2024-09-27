from typing import List, Optional

import re
import logging

from datetime import datetime
from operator import itemgetter

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_any_role
from discord.app_commands import autocomplete, Choice, choices, Range

from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

from mp2i.utils import database
from mp2i.models import SchoolModel
from sqlalchemy import insert, select

SCHOOL_REGEX = re.compile(r"^.+[|@] *(?P<prepa>.*)$")

logger = logging.getLogger(__name__)


class School(Cog):
    """
    Interface to manage schools.
    """

    def __init__(self, bot):
        self.bot = bot
        cpge_list = (
            database.execute(select(SchoolModel).where(SchoolModel.type == "cpge"))
            .scalars()
            .all()
        )
        self.high_schools = [x.name for x in cpge_list]
        engineering_school_list = (
            database.execute(
                select(SchoolModel).where(SchoolModel.type == "engineering")
            )
            .scalars()
            .all()
        )
        self.engineering_schools = [x.name for x in engineering_school_list]

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

    @hybrid_command(name="add_school")
    @guild_only()
    @has_any_role("Administrateur", "Moderateur")
    @choices(
        type=[
            Choice(name="Lycée", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    async def add_school(self, ctx, type: str, school: str):
        """
        Ajoute un lycée/école dans la base de donnée

        Parameters
        ----------
        type : Lycée ou École d'ingénieur
        school: Le lycée/école à ajouter.
        """
        if type == "cpge":
            if school in self.high_schools:
                await ctx.reply("Le lycée existe déjà", ephemeral=True)
                return
            database.execute(insert(SchoolModel).values(type="cpge", name=school))
            self.high_schools.append(school)
        else:
            if school in self.engineering_schools:
                await ctx.reply("L'école d'ingénieur existe déjà", ephemeral=True)
                return
            database.execute(
                insert(SchoolModel).values(type="engineering", name=school)
            )
            self.engineering_schools.append(school)

        await ctx.reply(f"{school} a bien été ajouté dans {type}")

    @hybrid_command(name="school")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @autocomplete(school=autocomplete_school)
    @choices(
        type=[
            Choice(name="Lycée", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    async def school_selection(
        self, ctx, type: str, school: str, user: Optional[discord.Member] = None
    ):
        """
        Associe un lycée/une école à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        type : Lycée ou école d'ingénieur
        school: Le lycée/école à associer.
        user: Réservé aux Administrateurs et Modérateurs
            L'utilisateur à qui on associe le lycée (par défaut, l'auteur de la commande)
        """
        if type == "cpge":
            if school not in self.high_schools and school != "Aucun":
                await ctx.reply("Le nom de lycée n'est pas valide", ephemeral=True)
                return
        else:
            if school not in self.engineering_schools and school != "Aucun":
                await ctx.reply("Le nom d'école n'est pas valide", ephemeral=True)
                return

        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
        elif ctx.author.guild_permissions.manage_roles:
            member = MemberWrapper(user)
        else:
            await ctx.reply("Vous n'avez pas les droits suffisants.", ephemeral=True)
            return

        if school == "Aucun":
            response = "Vous ne faites plus partie d'aucune école."
            school_id = -1
        else:
            response = f"Vous faites maintenant partie de l'école {school}."
            school_id = (
                database.execute(
                    select(SchoolModel)
                    .where(SchoolModel.name == school)
                    .where(SchoolModel.type == type)
                )
                .scalar_one()
                .id
            )
        if type == "cpge":
            member.high_school = school_id
        else:
            member.engineering_school = school_id

        await ctx.reply(response, ephemeral=True)

    @hybrid_command(name="generation")
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
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
            Choice(name="Lycée", value="cpge"),
            Choice(name="École d'ingénieur", value="engineering"),
        ]
    )
    async def school_members(self, ctx, type: str, school: str):
        """
        Affiche les étudiants d'une école donnée.
        """
        guild = GuildWrapper(ctx.guild)
        if type == "cpge":
            students = [
                member
                for member in map(MemberWrapper, guild.members)
                if member.exists() and member.high_school == school
            ]
        else:
            students = [
                member
                for member in map(MemberWrapper, guild.members)
                if member.exists() and member.engineering_school == school
            ]
        if not students:
            await ctx.reply(f"{school} n'a aucun étudiant sur ce serveur.")
            return

        content = f"Nombre d'étudiants : {len(students)}\n"
        for member in students:
            content += f"- `{member.name}`・{member.mention}\n"

        embed = discord.Embed(
            title=f"Liste des étudiants du lycée {school}",
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
            if member.exists() and member.high_school != -1:
                school = (
                    database.execute(
                        select(SchoolModel)
                        .where(SchoolModel.id == member.high_school)
                        .where(SchoolModel.type == "cpge")
                    )
                    .first()[0]
                    .name
                )
                referents.append((member, school))

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
