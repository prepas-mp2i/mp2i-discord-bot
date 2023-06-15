from functools import cache
from typing import Optional, Dict

import discord
import sqlalchemy.exc
from sqlalchemy import insert, select, update

from mp2i import CONFIG
from mp2i.utils import database
from mp2i.models import GuildModel
from mp2i.utils.dotdict import DefaultDotDict


class GuildWrapper:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.config = DefaultDotDict(dict, CONFIG).guilds[guild.id]
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

    @cache
    def get_member_by_name(self, member: str) -> Optional[discord.Member]:
        return discord.utils.get(self.members, name=member)

    @cache
    def get_role_by_emoji_name(self, name: str) -> Optional[Dict[str, str]]:
        return discord.utils.get(self.config.roles.values(), emoji=name)

    @cache
    def get_role_by_name(self, name: str) -> Optional[Dict[str, str]]:
        return discord.utils.get(self.config.roles.values(), emoji=name)

    def get_role_of_member(self, member: discord.Member) -> Optional[str]:
        for role_id, role in self.config.roles.items():
            if role := member.get_role(role_id):
                return role
        return None

    @cache
    def get_emoji_by_name(self, name: str) -> Optional[discord.Emoji]:
        return discord.utils.get(self.emojis, name=name)

    @cache
    def get_log_channel(self) -> Optional[discord.TextChannel]:
        return discord.utils.get(self.text_channels, id=self.config.channels.log)

    @property
    def roles_message_id(self) -> Optional[int]:
        return self.__model.roles_message_id

    @roles_message_id.setter
    def roles_message_id(self, message_id: Optional[int]):
        self.update(roles_message_id=message_id)
