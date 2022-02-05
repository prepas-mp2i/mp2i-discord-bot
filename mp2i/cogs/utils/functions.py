import logging
from typing import Optional

import discord

logger = logging.getLogger(__name__)


def get_member_by_name(guild: discord.Guild, member: str) -> Optional[discord.Member]:
    try:
        return discord.utils.get(guild.members, name=member)
    except AttributeError:
        return None


def get_member_by_id(guild: discord.Guild, member: int) -> Optional[discord.Member]:
    try:
        return discord.utils.get(guild.members, id=member)
    except AttributeError:
        return None


def get_role_by_name(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    try:
        return discord.utils.get(guild.roles, name=name)
    except AttributeError:
        return None


def is_suggestion_channel(channel: discord.Channel) -> bool:
    return "suggestion" in channel.name
