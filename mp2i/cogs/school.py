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
        with open(STATIC_DIR / "text/cpge.txt", encoding="UTF-8") as f:
            self.high_schools = f.read().splitlines()
        with open(STATIC_DIR / "text/ecole_inge.txt", encoding="UTF-8") as f:
            self.engineering_schools = f.read().splitlines()

    async def autocomplete_school(
        self, interaction: discord.Interaction, current: str
    ) -> List[Choice[str]]:
        type = interaction.namespace.type
        if type == "lycée":
            schools = self.high_schools
        else :
            schools = self.engineering_schools
        return [
            Choice(name=choice, value=choice)
            for choice in schools
            if current.lower() in choice.lower()
        ]

    @hybrid_command(name="school")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @autocomplete(school=autocomplete_school)
    @choices(type=[
            Choice(name='lycée', value='lycée'),
            Choice(name='école d\'ingénieur', value='école d\'ingénieur'),
        ])
    async def school_selection(
        self, ctx, type: str, school: str, user: Optional[discord.Member] = None
    ):
        """
        Associe un lycée/une école à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        type : Lycée ou école d'ingénieur
        school: Le lycée à associer.
        user: Réservé aux modérateurs
            L'utilisateur à qui on associe le lycée (par défaut, l'auteur de la commande)
        """
        if type == 'lycée':
            schools = self.high_schools
            messages = ["du lycée","aucun lycée"]
        else:
            schools = self.engineering_schools
            messages = ["de l'école d'ingénieur","aucune école d'ingénieur"]
        if school not in schools and school != "Aucun":
            await ctx.reply(f"Le nom {messages[0]} n'est pas valide", ephemeral=True)
            return

        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
            if school == "Aucun":
                member_school = None
                response = f"Vous ne faites plus partie {messages[1]}"
            else:
                member_school = school
                response = f"Vous faites maintenant partie {messages[0]} {school}."
            if type == 'lycée':
                member.high_school = member_school
            else:
                member.engineering_school = member_school

        elif any(r.name in ("Administrateur", "Modérateur") for r in ctx.author.roles):
            member = MemberWrapper(user)
            if school == "Aucun":
                member_school = None
                response = f"{user.mention} ne fait plus partie d'{messages[1]}."
            else:
                member_school = school
                response = f"{user.mention} fait maintenant partie {messages[0]} {school}"
            if type == 'lycée':
                member.high_school = member_school
            else:
                member.engineering_school = member_school
        else:
            response = "Vous n'avez pas les droits suffisants."

        await ctx.reply(response, ephemeral=True)
    
    @hybrid_command(name="gen")
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @guild_only()
    async def generation(self, ctx, gen : Range[int,2021,datetime.now().year], user: Optional[discord.Member] = None):
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
            await ctx.reply(f"Vous faites maintenant partie de la génération {gen} !")
        elif any(r.name in ("Administrateur", "Modérateur") for r in ctx.author.roles):
            member = MemberWrapper(user)
            member.generation = gen
            await ctx.reply(f"{user.mention} fait maintenant partie de la génération {gen} !")
        else:
            await ctx.reply("Vous n'avez pas les droits suffisants.")
        


    @hybrid_command(name="members")
    @guild_only()
    @autocomplete(school=autocomplete_school)
    @choices(type=[
        Choice(name='lycée', value='lycée'),
        Choice(name='école d\'ingénieur', value='école d\'ingénieur'),
    ])
    async def school_members(self, ctx, type:str, school: str):
        """
        Affiche les étudiants d'une école donnée.
        """
        guild = GuildWrapper(ctx.guild)
        if type == 'lycée':
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
            if member.exists() and member.high_school != "Aucun":
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
