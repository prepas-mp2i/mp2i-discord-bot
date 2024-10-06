from functools import wraps


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
