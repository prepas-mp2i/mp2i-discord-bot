import datetime

import discord
from sqlalchemy import insert

from mp2i.models import MessageModel
from mp2i.utils import database


class MessageWrapper:
    def __init__(self, message: discord.Message):
        self.message = message

    def __getattr__(self, name: str):
        return getattr(self.message, name)

    def insert(self) -> None:
        """
        Inserts a message row in messages table
        """
        if isinstance(self.message.channel, discord.DMChannel):
            channel = "DMChannel"
        else:
            channel = self.message.channel.name

        database.execute(
            insert(MessageModel).values(
                author_id=self.message.author.id,
                guild_id=self.message.guild.id,
                channel=channel,
                date=datetime.datetime.now(),
                content=self.message.content,
            )
        )
