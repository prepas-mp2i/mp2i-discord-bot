from functools import wraps
from discord.ext.commands.errors import NoPrivateMessage, MissingAnyRole
from discord.ext.commands import check

from mp2i.wrappers.guild import GuildWrapper

def defer(ephemeral: bool = False):
    """
    Decorator that defers the response of a command.
    """

    def decorator(func):
        @wraps(func)
        async def command_wrapper(self, ctx, *args, **kwargs):
            await ctx.defer(ephemeral=ephemeral)
            await func(self, ctx, *args, **kwargs)

        return command_wrapper

    return decorator

def has_any_role(*items: str):
    """
    Decorator that check if the user has any of the specified roles.
    """

    def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessage()

        # ctx.guild is None doesn't narrow ctx.author to Member
        guild = GuildWrapper(ctx.guild)
        if any(
            guild.get_role_by_qualifier(item) in ctx.author.roles
            for item in items
        ):
            return True
        raise MissingAnyRole(list(items))

    return check(predicate)
