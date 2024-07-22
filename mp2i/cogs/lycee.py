import logging

import discord
from discord.ext.commands import (
    Cog,
    hybrid_command,
    guild_only,
    has_any_role,
    has_permissions,
)
from discord import app_commands
from typing import List, Optional

from mp2i import STATIC_DIR
from mp2i.utils import database
from mp2i.wrappers.member import MemberWrapper
from mp2i.wrappers.guild import GuildWrapper

logger = logging.getLogger(__name__)


class Lycee(Cog):
    """
    Association d'un membre et d'un lycée
    """

    def __init__(self, bot):
        self.bot = bot
        with open(STATIC_DIR / "text/Liste_lycee_MP2I.txt", encoding="UTF-8") as f:
            self.lycees = f.read().splitlines()

    async def autocomplete_lycee(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=choice, value=choice)
            for choice in self.lycees
            if current.lower() in choice.lower()
        ]

    @hybrid_command(name="chooselycee")
    @guild_only()
    @has_any_role("MP2I", "MPI", "Ex MPI", "Moderateur", "Administrateur")
    @app_commands.autocomplete(lycee=autocomplete_lycee)
    async def choose_lycee(
        self, ctx, lycee: str, user: Optional[discord.Member] = None
    ):
        """
        Associe un lycée à un membre (Aucun pour supprimer l'association)

        Parameters
        ----------
        lycee : str
            Le lycée à associer
        user : Optional[discord.Member]
            Réservé aux modérateurs
            L'utilisateur à qui on associe le lycéee (avec soi-même l'argument est vide)
        """
        if not lycee in self.lycees and lycee != "Aucun":
            await ctx.reply("Le nom du lycée n'est pas valide", ephemeral=True)
            return
        if user is None or user == ctx.author:
            member = MemberWrapper(ctx.author)
            if lycee == "Aucun":
                member.lycee = None
                await ctx.reply(
                    "Vous ne faites plus partie aucun lycée", ephemeral=True
                )
            else:
                member.lycee = lycee
                await ctx.reply(
                    f"Vous faites maintenant partie du lycée {lycee}", ephemeral=True
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
                if lycee == "Aucun":
                    member.lycee = None
                    await ctx.reply(
                        "{user.mention} ne fait plus partie aucun lycée", ephemeral=True
                    )
                else:
                    member.lycee = lycee
                    await ctx.reply(
                        f"{user.mention} fait maintenant partie du lycée {lycee}",
                        ephemeral=True,
                    )
            else:
                await ctx.reply(
                    f"Vous n'avez pas les droits suffisants pour modifier le lycée d'autres personnes",
                    ephemeral=True,
                )

    @hybrid_command(name="lycees")
    @guild_only()
    async def lycees(self, ctx):
        """
        Affiche le nombre de étudiants étant ou ayant été en MP2I/MPI réparti par lycée
        """
        def members_lycee(ctx):
            for member in map(MemberWrapper, ctx.guild.members):
                if (not member.bot) and member.exists() and member.lycee != "Aucun":
                    yield member.lycee

        count = dict((i, 0) for i in self.lycees)
        for m in members_lycee(ctx):
            count[m] += 1
        content = ""
        for lycee, nb_studient in count.items():
            plural = "s" if nb_studient > 1 else ""
            if nb_studient > 0:
                content += f"**{lycee}** : {nb_studient} étudiant{plural}\n"
        title = "Nombre de membres du serveur par lycée"
        embed = discord.Embed(
            colour=0x2BFAFA,
            title=title,
            description=content,
        )
        await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Lycee(bot))
