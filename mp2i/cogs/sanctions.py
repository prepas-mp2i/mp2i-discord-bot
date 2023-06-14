from datetime import datetime
from typing import Optional
from venv import logger

import discord
from discord.ext.commands import Cog, command, guild_only, has_permissions
from sqlalchemy import insert, select

from mp2i.wrappers.member import MemberWrapper
from mp2i.utils import database
from mp2i.models import SanctionModel


class Sanction(Cog):
    """
    Offers interface to manage sanctions to users
    """

    def __init__(self, bot):
        self.bot = bot

    @command(name="warn")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, dm: str, visible: str, 
                   *, reason: Optional[str]) -> None:
        """
        Avertit un utilisateur pour une raison donnée.
        """
        await ctx.message.delete() # C'est la marmelade de ma grand mère
        database.execute(           
            insert(SanctionModel).values(
                by_id=ctx.author.id,
                to_id=member.id,
                guild_id=ctx.guild.id,
                date=datetime.now(),
                type="warn",
                reason=reason
            )
        )
        if visible == "oui":
            embed = discord.Embed(
                title=f"{member.mention} a reçu un avertissement",
                colour=0xFF0000,
                timestamp=datetime.now()
            )
            if reason:
                embed.add_field(name="Raison", value=reason)
            await ctx.send(embed=embed)
        if dm == "oui":
            if reason:
                await member.send("Vous avez reçu un avertissement pour la raison suivante: \n"
                                f">>> {reason}")
            else:
                await member.send("Vous avez reçu un avertissement.")
        
    @command(name="sanctions_list")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def sanctions_list(self, ctx, member: Optional[discord.Member]):
        """
        Liste les sanctions reçues par un membre.
        """
        if member:
            request = select(SanctionModel).where(
                SanctionModel.to_id == member.id,
                SanctionModel.guild_id == ctx.guild.id
            )
        else:   
            request = select(SanctionModel).where(
                SanctionModel.guild_id == ctx.guild.id
            )
        sanctions = database.execute(request).scalars().all()

        for sanction in sanctions:
            by = ctx.guild.get_member(sanction.by_id)
            to = ctx.guild.get_member(sanction.to_id)
            embed = discord.Embed(
                title=f"{to.mention} a reçu un {sanction.type} par {by.name}",
                colour=0xFF0000,
                timestamp=sanction.date
            )
            if sanction.reason:
                embed.add_field(name="Raison", value=sanction.reason)
            await ctx.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Sanction(bot))