from operator import attrgetter
from typing import Optional

import discord
from discord.ext.commands import Cog, CommandError, hybrid_command, guild_only


class Help(Cog):
    """
    Sends this help message
    """

    def __init__(self, bot):
        self.bot = bot

    @hybrid_command(name="help")
    @guild_only()
    async def help(self, ctx, *, command: Optional[str] = None) -> None:
        """
        Affiche les commandes du bot.

        Parameters
        ----------
        command : str, optional
            Nom de la commande dont on veut afficher l'aide.
        """
        if command is not None:
            await self.help_command(ctx, command)
            return

        sorted_commands = sorted(
            await self._filtered_commands(ctx), key=attrgetter("name")
        )
        max_size = max(len(command.name) for command in sorted_commands)

        content = ""
        for command in sorted_commands:
            content += f"`/{command.name:<{max_size+1}}` {command.short_doc}\n"

        content += "\nPour l'aide sur une commande, tapez `/help <commande>`."
        embed = discord.Embed(
            title=f"Liste des commandes du serveur {ctx.guild.name}",
            description=content,
            color=0xEE22EE,
        )
        await ctx.reply(embed=embed, ephemeral=True)

    async def help_command(self, ctx, command_name: str) -> None:
        """
        Shows help for a specific command.
        """
        command = self.bot.get_command(command_name)
        embed = discord.Embed(
            title=f"Commande `/{command_name}`",
            description=command.help,
            color=0xEE22EE,
        )
        await ctx.reply(embed=embed, ephemeral=True)

    async def _filtered_commands(self, ctx) -> list:
        """
        Filters commands that the user can use.
        """

        async def can_run(command) -> bool:
            try:
                return await command.can_run(ctx)
            except CommandError:
                return False

        return [c for c in self.bot.commands if await can_run(c)]


async def setup(bot):
    await bot.add_cog(Help(bot))
