import re
import logging
from itertools import cycle
from typing import Optional
from datetime import datetime

import discord
from discord.ext import tasks
from discord.ext.commands import Cog, command, guild_only, is_owner, has_permissions

from mp2i.wrappers.guild import GuildWrapper
from mp2i.wrappers.member import MemberWrapper

from .utils import youtube

logger = logging.getLogger(__name__)


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status = cycle((discord.Game(name=f"{bot.command_prefix}help"),))

    @command(name="reset_status")
    @guild_only()
    @is_owner()
    async def reset_status(self, ctx) -> None:
        """
        Réinitialise le status du bot à =help
        """
        help_status = f"{self.bot.command_prefix}help"
        await self.bot.change_presence(activity=discord.Game(help_status))
            

    @command(name="status")
    @guild_only()
    @is_owner()
    async def change_status(self, ctx, *, query: str) -> None:
        """
        Change le status du bot par n vidéos correspondantes à la recherche
        """
        try:
            video = next(youtube.search(query, n=1))
            activity = discord.Streaming(**video)
            await self.bot.change_presence(activity=activity)

        except StopIteration:
            await ctx.send("Changement de statut du bot impossible.")
        
        except discord.errors.HTTPException:
            logger.error("Can't change bot presence")
            

    @Cog.listener("on_ready")
    async def before_loop_status(self) -> None:
        self.loop_status.start()

    @command()
    @guild_only()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, n: int = 1) -> None:
        """
        Supprime les n derniers messages du salon
        """
        await ctx.channel.purge(limit=int(n) + 1)

    @command()
    @guild_only()
    async def send(self, ctx, *, message: str) -> None:
        """
        Envoie un message dans le salon actuel
        """
        await ctx.send(message)
        await ctx.message.delete()

    @command(name="profile", aliases=["member_info"])
    @guild_only()
    async def profile(self, ctx, member: Optional[discord.Member] = None) -> None:
        """
        Consulte les infos d'un membre
        """
        member = MemberWrapper(member or ctx.author)
        embed = discord.Embed(title="Profil", colour=int(member.profile_color, 16))
        embed.set_author(name=member.name)
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Pseudo", value=member.mention, inline=True)
        embed.add_field(
            name="Membre depuis", value=f"{member.joined_at:%d/%m/%Y}", inline=True
        )
        embed.add_field(name="Messages", value=member.messages_count, inline=True)
        embed.add_field(
            name="Rôles",
            inline=True,
            value=" ".join(r.mention for r in member.roles if r.name != "@everyone"),
        )
        await ctx.send(embed=embed)


    @command(name="profile_color")
    @guild_only()
    async def change_profile_color(self, ctx, color: str) -> None:
        """
        Change la couleur de profil
        """
        member = MemberWrapper(ctx.author)
        member.profile_color = color.upper().strip()
        await ctx.send(f"Couleur de profil changée en #{member.profile_color}.")

    @command(aliases=["server_profile"])
    @guild_only()
    async def server_info(self, ctx) -> None:
        """
        Consulte les infos du serveur
        """
        guild = GuildWrapper(ctx.guild)
        embed = discord.Embed(title="Infos du serveur", colour=0xFFA325)
        embed.set_author(name=guild.name)
        embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Membres", value=len(guild.members), inline=True)

        for role_id, role in guild.config.roles.items():
            number = len(guild.get_role(role_id).members)
            embed.add_field(name=f"{role['name']}", value=number, inline=True)
        await ctx.send(embed=embed)

    @command()
    @guild_only()
    async def referents(self, ctx) -> None:
        """
        Liste les étudiants référents du serveur
        """
        content = ""
        for member in ctx.guild.members:
            if discord.utils.get(member.roles, name="Référent"):
                content += f"- {member.nick} (`{member.name}"
                if member.disciminator != 0:
                    content += f"#{member.discriminator}"
                content += f"` - {member.status})\n"
                
        embed = discord.Embed(
            title=f"Liste des étudiants référents du serveur {ctx.guild.name}",
            colour=0xFF66FF,
            description=content,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=self.bot.user.name)
        await ctx.send(embed=embed)

    @Cog.listener("on_message")
    async def unbinarize(self, msg: discord.Message):
        """
        Vérifie si le message est un texte binaire et le convertit en ASCII
        """
        if not re.fullmatch(r"([01]{8}\s?)+", msg.content):
            return
        await msg.channel.send(
            f"{msg.author.mention}: "
            + "".join(chr(int(b, 2)) for b in re.findall("[01]{8}", msg.content))
        )


async def setup(bot) -> None:
    await bot.add_cog(Commands(bot))
