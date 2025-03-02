import logging

from discord.ext.commands import Cog, errors

from mp2i.utils.discord import defer

logger = logging.getLogger(__name__)


class ErrorHandler(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    @defer(ephemeral=True)
    async def on_command_error(self, ctx, error) -> None:
        """
        Provides generic command error handling.

        Error handling is deferred to any local error handler, if present.
        This is done by checking for the presence of a `handled` attribute on the error.
        """
        if isinstance(error, errors.ConversionError):
            logger.debug(
                f"The {error.original} argument given by {ctx.author}cannot be "
                f"converted into {error.converter}"
            )
            await ctx.reply("Votre argument est invalide.")

        elif ctx.command.has_error_handler():
            logger.debug(f"Local error handler for {ctx.command} has been called")
        
        elif isinstance(error, errors.MissingAnyRole):
            logger.debug(f"{error}")
            await ctx.reply("Vous n'avez pas la permission d'utiliser cette commande.")

        elif isinstance(error, errors.NoPrivateMessage):
            logger.debug(f"{error}")
            await ctx.reply("Cette commande ne peut pas être utilisée en message privé.")

        elif not isinstance(error, errors.CommandNotFound):
            logger.error(f"{error}")
            await ctx.reply(
                "Une erreur interne est survenue, veuillez contacter un Administrateur."
            )


async def setup(bot) -> None:
    """
    Loads the ErrorHandler cog.
    """
    await bot.add_cog(ErrorHandler(bot))
