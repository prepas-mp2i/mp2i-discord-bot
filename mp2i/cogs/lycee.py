import logging

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_permissions
from discord import app_commands
from typing import List

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
        with open(STATIC_DIR / "text/Liste_lycee_MP2I.txt") as f:
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
    @guild_only
    @app_commands.autocomplete(item=autocomplete_lycee)
    async def choose_lycee(self, interaction: discord.Interaction, lycee: str):
        """
        Associe un lycée à soi-même

        Parameters
        ----------
        lycee : str
            Le lycée à associer
        """
        if not lycee in self.lycees:
            await interaction.response.send_message("Le nom du lycée n'est pas valide")
            return
        member = MemberWrapper(interaction.user)
        if not member.exists():
            logger.warning(f"The user {member.name} was not a registered member")
            member.register()
        member.lycee = lycee
        await interaction.response.send_message(
            f"Vous faites maintenant partie du lycée {lycee}"
        )
