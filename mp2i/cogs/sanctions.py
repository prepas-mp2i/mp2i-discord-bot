import logging
from datetime import datetime
from typing import Optional

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_permissions
from sqlalchemy import insert, select, delete

from mp2i.utils import database
from mp2i.models import SanctionModel as SM

logger = logging.getLogger(__name__)


class Sanction(Cog):
    """
    Offers interface to manage sanctions to users
    """

    def __init__(self, bot):
        self.bot = bot

    @hybrid_command(name="warn")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, dm: str, visible: str, *,
                   reason: Optional[str]) -> None:  # fmt: skip
        """
        Avertit un utilisateur pour une raison donnée.

        Parameters
        ----------
        member : discord.Member
            L'utilisateur à avertir.
        dm : str
            Si oui, l'utilisateur sera averti par message privé.
        visible : str
            Si oui, l'avertissement sera visible dans le salon des sanctions.
        reason : Optional[str]
            La raison de l'avertissement.
        """
        database.execute(
            insert(SM).values(
                by_id=ctx.author.id,
                to_id=member.id,
                guild_id=ctx.guild.id,
                date=datetime.now(),
                type="warn",
                reason=reason,
            )
        )
        if dm == "oui":
            if reason:
                await member.send(
                    "Vous avez reçu un avertissement pour la raison suivante: \n"
                    f">>> {reason}"
                )
            else:
                await member.send("Vous avez reçu un avertissement.")

        embed = discord.Embed(
            title=f"{member.mention} a reçu un avertissement",
            colour=0xFF00FF,
            timestamp=datetime.now(),
        )
        if reason:
            embed.add_field(name="Raison", value=reason)
        # If ephemeral is True, the message will only be visible to the author
        await ctx.send(embed=embed, ephemeral=visible != "oui")

    @hybrid_command(name="warnlist")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def warnlist(self, ctx, member: Optional[discord.Member]) -> None:
        """
        Liste les sanctions reçues par un membre.

        Parameters
        ----------
        member : Optional[discord.Member]
            Le membre dont on veut lister les sanctions.
        """
        if member:
            request = select(SM).where(
                SM.to_id == member.id, SM.guild_id == ctx.guild.id, SM.type == "warn"
            )
            title = f"Liste des avertissements de {member.name}"
        else:
            request = select(SM).where(SM.guild_id == ctx.guild.id, SM.type == "warn")
            title = "Liste des avertissements du serveur"

        sanctions = database.execute(request).scalars().all()
        content = f"**Nombre d'avertissements :** {len(sanctions)}\n\n"

        for sanction in sanctions:
            content += f"**{sanction.id}** ━ Le {sanction.date:%d/%m/%Y à %H:%M}\n"
            if not member:
                to = ctx.guild.get_member(sanction.to_id)
                content += f"> **Membre :** {to.mention}\n"

            by = ctx.guild.get_member(sanction.by_id)
            content += f"> **Modérateur :** {by.mention}\n"
            if sanction.reason:
                content += f"> **Raison :** {sanction.reason}\n"
            content += "\n"

        embed = discord.Embed(
            title=title, description=content, colour=0xFF00FF, timestamp=datetime.now()
        )
        await ctx.send(embed=embed)

    @hybrid_command(name="unwarn")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def unwarn(self, ctx, id: int) -> None:
        """
        Supprime un avertissement.

        Parameters
        ----------
        id : int
            L'identifiant de l'avertissement à supprimer.
        """
        database.execute(delete(SM).where(SM.id == id))
        await ctx.send(f"L'avertissement {id} a été supprimé.")


async def setup(bot) -> None:
    await bot.add_cog(Sanction(bot))
