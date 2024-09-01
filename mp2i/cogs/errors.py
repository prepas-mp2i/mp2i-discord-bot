import logging

from discord.ext.commands import Cog, errors

logger = logging.getLogger(__name__)


class ErrorHandler(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
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
            await ctx.send("Votre argument est invalide.")

        elif hasattr(error, "handled"):
            logger.debug(f"Local error handler for {ctx.command} has been called")

        else:
            logger.error(f"{error.original}")
            await ctx.reply(
                "Une erreur interne est survenue, veuillez contacter un Administrateur.",
                ephemeral=True,
            )


async def setup(bot) -> None:
    """
    Loads the ErrorHandler cog.
    """
    await bot.add_cog(ErrorHandler(bot))
