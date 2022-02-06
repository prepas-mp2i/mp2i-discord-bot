import logging
from typing import Optional
from functools import cache

import discord

logger = logging.getLogger(__name__)


@cache
def get_member_by_name(guild: discord.Guild, name: str) -> Optional[discord.Member]:
    return discord.utils.get(guild.members, name=name)


@cache
def get_member_by_id(guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
    return discord.utils.get(guild.members, id=member_id)


@cache
def get_role_by_name(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    return discord.utils.get(guild.roles, name=name)


@cache
def get_emoji_by_name(guild: discord.Guild, name: str) -> Optional[discord.Emoji]:
    return discord.utils.get(guild.emojis, name=name)
