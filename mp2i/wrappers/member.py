from __future__ import annotations

from typing import NoReturn, Optional

import discord
import sqlalchemy.exc
from sqlalchemy import insert, select, update

from mp2i.models import MemberModel
from mp2i.utils import database
from mp2i.cogs.utils.functions import get_role_by_name


class MemberWrapper:
    """
    A class that wraps a Discord member and offers an interface
    for the database for attributes like XP, level, roles and blacklist date
    """

    def __init__(self, member: discord.Member):
        """
        Représente a member with additional attributes
        """
        self.member = member
        self.guild = member.guild
        self.__model = self._fetch()

    def __getattr__(self, name: str):
        return getattr(self.member, name)

    def _fetch(self) -> Optional[MemberModel]:
        """
        Fetch from the database and returns the member if exists
        """
        try:
            return database.execute(
                select(MemberModel).where(MemberModel.id == self.member.id)
            ).scalar_one()
        except sqlalchemy.exc.NoResultFound:
            return None

    def update(self, **kwargs):
        """
        Accept keyword arguments only matching with a column in members table
        """
        database.execute(
            update(MemberModel).where(MemberModel.id == self.member.id).values(**kwargs)
        )

    def register(self) -> NoReturn:
        """
        Insert the member in table, with optionals attributes
        """
        database.execute(
            insert(MemberModel).values(id=self.member.id, name=self.member.name)
        )
        self.__model = self._fetch()  # Update the model

    def exists(self) -> bool:
        return self.__model is not None

    @property
    def role(self) -> discord.Role:
        return get_role_by_name(self.guild, self.__model.role.name)

    @role.setter
    def role(self, role: discord.Role | str):
        role_name = role if isinstance(role, str) else role.name
        self.update(role=role_name)
