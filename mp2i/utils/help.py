import itertools

import discord
from discord.ext.commands import DefaultHelpCommand, Paginator


class CustomHelpCommand(DefaultHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.paginator = Paginator(prefix="", suffix="")

    async def send_bot_help(self, _):
        """
        Send help message when help command is invoked
        """

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog else "Autres commandes"

        bot = self.context.bot
        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)
        max_size = self.get_max_size(filtered)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name)
            self.add_indented_commands(commands, heading=category, max_size=max_size)

        self.paginator.add_line(
            f"\nTapez `{bot.command_prefix}{self.invoked_with} command`"
            " pour plus d'infos sur une commande.\n"
        )
        await self.send_pages()

    def add_indented_commands(self, commands, *, heading, max_size):
        """
        Indents a list of commands after the specified heading.
        """
        self.paginator.add_line(f"**\n{heading}**")
        prefix = self.context.bot.command_prefix

        for command in commands:
            entry = f"`{prefix}{command.name:<{max_size+1}}` {command.short_doc}"
            self.paginator.add_line(self.shorten_text(entry))

    async def send_pages(self):
        """
        A helper utility to send the page output from paginator
        to the destination.
        """
        destination = self.get_destination()
        title = f"Liste des commandes du serveur {self.context.guild.name}"

        for page in self.paginator.pages:
            embed = discord.Embed(title=title, description=page, color=0xEE22EE)
            await destination.send(embed=embed)
