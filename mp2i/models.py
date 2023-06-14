from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Integer, BigInteger, Column, DateTime, String, Text, ForeignKey
from sqlalchemy.schema import PrimaryKeyConstraint, ForeignKeyConstraint

Base = declarative_base()


class GuildModel(Base):
    __tablename__ = "guilds"

    id: int = Column(BigInteger, primary_key=True)
    name: str = Column(String(50))
    members = relationship("MemberModel", cascade="all, delete")
    roles_message_id: int = Column(BigInteger, unique=True, nullable=True)

    def __repr__(self):
        return f"Guild(id={self.id}, name={self.name})"


class MemberModel(Base):
    __tablename__ = "members"
    __table_args__ = (PrimaryKeyConstraint("id", "guild_id", name="members_pkey"),)
    id: int = Column(BigInteger)
    guild_id: int = Column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    name: str = Column(String(50))
    role: str = Column(String(50), nullable=True)
    messages_count: int = Column(Integer, default=0)
    profile_color: str = Column(String(8), nullable=True)

    def __repr__(self):
        return f"Member(id={self.id}, name={self.name}, role={self.role})"


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ("author_id", "guild_id"),
            ("members.id", "members.guild_id"),
            ondelete="CASCADE",
            name="messages_author_id_guild_id_fkey",
        ),
    )
    id: int = Column(BigInteger, primary_key=True)
    guild_id: int = Column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    author_id: int = Column(BigInteger)
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
    author_id: int = Column(BigInteger)
    guild_id: int = Column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    date = Column(DateTime, nullable=True)
    description: str = Column(Text)

    def __repr__(self):
        return (
            f"Suggestion(author={self.author_id}, description={self.description:30.30}"
        )

class SanctionModel(Base):
    __tablename__ = "sanctions"
    __table_args__ = (
        ForeignKeyConstraint(
            ("to_id", "guild_id"),
            ("members.id", "members.guild_id"),
            ondelete="CASCADE",
            name="sanctions_to_id_guild_id_fkey",
        ),
    )
    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    by_id: int = Column(BigInteger)
    to_id: int = Column(BigInteger)
    guild_id: int = Column(BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"))
    date = Column(DateTime)
    type: str = Column(String(50))
    reason: str = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"Sanction(by={self.by_id}, to={self.to_id}, type={self.type}," 
            f"description={self.description:30.30}"
        )