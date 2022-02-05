import datetime
from typing import NoReturn

import discord
from sqlalchemy import insert

from mp2i.models import MessageModel
from mp2i.utils import database


class MessageWrapper:
    def __init__(self, message: discord.Message):
        self.message = message

    def __getattr__(self, name: str):
        return getattr(self.message, name)

    def insert(self) -> NoReturn:
        """
        Inserts a message row in messages table
        """
        if isinstance(self.message.channel, discord.DMChannel):
            channel, guild_id = "DMChannel", None
        else:
            channel, guild_id = self.message.channel.name, self.message.guild.id

        database.execute(
            insert(MessageModel).values(
                guild_id=guild_id,
                author_id=self.message.author.id,
                channel=channel,
                date=datetime.datetime.now(),
                content=self.message.content,
            )
        )
