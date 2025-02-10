from functools import cache, cached_property
from typing import Optional, List

import discord
import sqlalchemy.exc
from sqlalchemy import insert, select, update

from mp2i import CONFIG
from mp2i.utils import database
from mp2i.models import GuildModel
from mp2i.utils.dotdict import DefaultDotDict


class GuildWrapper:
    """
    A class that wraps a Discord guild and offers an interface for the database
    guild model.
    """

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.config = DefaultDotDict(dict, CONFIG).guilds.get(guild.id)
        self.__model = self._fetch()

    def __getattr__(self, name: str):
        return getattr(self.guild, name)

    def _fetch(self) -> Optional[GuildModel]:
        """
        Fetch from the database and returns the guild if exists
        """
        try:
            return database.execute(
                select(GuildModel).where(GuildModel.id == self.guild.id)
            ).scalar_one()
        except sqlalchemy.exc.NoResultFound:
            return None

    def register(self) -> None:
        database.execute(
            insert(GuildModel).values(id=self.guild.id, name=self.guild.name)
        )
        self.__model = self._fetch()  # Update the model

    def update(self, **kwargs) -> None:
        """
        Accept keyword arguments only matching with a column in members table
        """
        database.execute(
            update(GuildModel).where(GuildModel.id == self.guild.id).values(**kwargs)
        )
        self.__model = self._fetch()

    def exists(self) -> bool:
        return self.__model is not None

    @cache
    def get_member_by_name(self, member: str) -> Optional[discord.Member]:
        return discord.utils.get(self.members, name=member)

    def get_role_by_qualifier(self, qualifier: str) -> Optional[discord.Role]:
        if not self.config or self.config.roles.get(qualifier) is None:
            return None
        return self.guild.get_role(self.config.roles[qualifier].id)

    def get_emoji_by_name(self, name: str) -> Optional[discord.Emoji]:
        return discord.utils.get(self.guild.emojis, name=name)

    @cached_property
    def choiceable_roles(self) -> List[str]:
        if not self.config:
            return []
        return [name for name, role in self.config.roles.items() if role.choice]

    @cached_property
    def log_channel(self) -> Optional[discord.TextChannel]:
        if not self.config:
            return None
        return self.guild.get_channel(self.config.channels.log)

    @cached_property
    def sanctions_log_channel(self) -> Optional[discord.TextChannel]:
        if not self.config:
            return None
        return self.guild.get_channel(self.config.channels.sanctions)

    @cached_property
    def suggestion_channel(self) -> Optional[discord.TextChannel]:
        if not self.config:
            return None
        return self.guild.get_channel(self.config.channels.suggestion)

    @cached_property
    def website_channel(self) -> Optional[discord.TextChannel]:
        if not self.config:
            return None
        return self.guild.get_channel(self.config.channels.website)

    @property
    def roles_message_id(self) -> Optional[int]:
        return self.__model.roles_message_id

    @roles_message_id.setter
    def roles_message_id(self, message_id: Optional[int]):
        self.update(roles_message_id=message_id)
