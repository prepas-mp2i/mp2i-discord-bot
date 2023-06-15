import logging
from typing import Optional

import discord
from discord.ext.commands import MemberConverter
import sqlalchemy.exc
from sqlalchemy import insert, select, update

from mp2i.models import MemberModel
from mp2i.utils import database

logger = logging.getLogger(__name__)


class MemberWrapper:
    """
    A class that wraps a Discord member and offers an interface
    for the database for attributes like XP, level, roles and blacklist date
    """

    DEFAULT_PROFILE_COLOR = "0000FF"

    def __init__(self, member: discord.Member):
        """
        Represents a member with additional attributes
        """
        self.member = member
        self.guild = member.guild
        self.__model = self._fetch()

    def __getattr__(self, name: str):
        return getattr(self.member, name)

    @classmethod
    async def convert(cls, ctx, member):
        member = await MemberConverter().convert(ctx, member)
        return cls(member)

    def _fetch(self) -> Optional[MemberModel]:
        """
        Fetch from the database and returns the member if exists
        """
        try:
            return database.execute(
                select(MemberModel).where(
                    MemberModel.id == self.member.id,
                    MemberModel.guild_id == self.guild.id,
                )
            ).scalar_one()
        except sqlalchemy.exc.NoResultFound:
            return None

    def update(self, **kwargs) -> None:
        """
        Accept keyword arguments only matching with a column in members table
        """
        database.execute(
            update(MemberModel)
            .where(
                MemberModel.id == self.member.id,
                MemberModel.guild_id == self.guild.id,
            )
            .values(**kwargs)
        )
        self.__model = self._fetch()

    def register(self, role: Optional[discord.Role] = None) -> None:
        """
        Insert the member in table, with optionals attributes
        """
        database.execute(
            insert(MemberModel).values(
                id=self.member.id,
                guild_id=self.guild.id,
                name=self.member.name,
                role=role.name,
            )
        )
        self.__model = self._fetch()  # Update the model

    def exists(self) -> bool:
        return self.__model is not None

    @property
    def role(self) -> Optional[discord.Role]:
        return discord.utils.get(self.guild.roles, name=self.__model.role)

    @property
    def messages_count(self) -> int:
        return self.__model.messages_count

    @messages_count.setter
    def messages_count(self, value: int) -> None:
        self.update(messages_count=value)

    @property
    def profile_color(self) -> str:
        return self.__model.profile_color or self.DEFAULT_PROFILE_COLOR

    @profile_color.setter
    def profile_color(self, value: str):
        self.update(profile_color=value)
