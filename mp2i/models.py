from sqlalchemy import BigInteger, Column, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class GuildModel(Base):
    __tablename__ = "guilds"

    id: int = Column(BigInteger, primary_key=True)
    name: str = Column(String(50), unique=True)
    message_roles_id: int = Column(BigInteger, unique=True, nullable=True)

    def __repr__(self):
        return f"Guild(id={self.id}, name={self.name})"


class Member(Base):
    __tablename__ = "members"

    id: int = Column(BigInteger, primary_key=True)
    name: str = Column(String(50), unique=True)
    role: str = Column(String(50), nullable=True)

    def __repr__(self):
        return f"Member(id={self.id}, name={self.name}, role={self.role})"


class Message(Base):
    __tablename__ = "messages"

    id: int = Column(BigInteger, primary_key=True)
    author_id: int = Column(BigInteger, ForeignKey("Member.id"))
    channel: str = Column(String(50))
    date = Column(DateTime)
    content: str = Column(Text, nullable=True)

    def __repr__(self):
        return "Message(author_id={}, channel={}, date={}, content={:30.30}".format(
            self.author_id, self.channel, self.date, self.content
        )


class SuggestionModel(Base):
    __tablename__ = "suggestions"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    author: str = Column(String(50))
    date = Column(DateTime, nullable=True)
    description: str = Column(Text)

    def __repr__(self):
        return f"Special(author={self.author}, description={self.description:30.30}"
