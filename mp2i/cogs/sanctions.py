import logging
from datetime import datetime
from typing import Optional

import discord
from discord.ext.commands import Cog, hybrid_command, guild_only, has_permissions
from sqlalchemy import insert, select, delete

from mp2i.utils import database
from mp2i.models import SanctionModel
from mp2i.wrappers.guild import GuildWrapper

logger = logging.getLogger(__name__)


class Sanction(Cog):
    """
    Offers interface to manage sanctions to users
    """

    def __init__(self, bot):
        self.bot = bot
        self.users = {}

    @hybrid_command(name="warn")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, dm: str, *,
                   reason: str) -> None:  # fmt: skip
        """
        Avertit un utilisateur pour une raison donnée.

        Parameters
        ----------
        member : discord.Member
            L'utilisateur à avertir.
        dm : str
            Si oui, l'utilisateur sera averti par message privé.
        reason : str
            La raison de l'avertissement.
        """
        database.execute(
            insert(SanctionModel).values(
                by_id=ctx.author.id,
                to_id=member.id,
                guild_id=ctx.guild.id,
                date=datetime.now(),
                type="warn",
                reason=reason,
            )
        )
        send_dm = dm == "oui"
        message_sent = False
        if send_dm:
            # Au cas où l'utilisateur visé a fermé ses messages privés.
            try:
                await member.send(
                    "Vous avez reçu un avertissement pour la raison suivante: \n"
                    f">>> {reason}"
                )
                message_sent = True
            except:
                message_sent = False

        embed = discord.Embed(
            title=f"{member.name} a reçu un avertissement",
            colour=0xFF00FF,
            timestamp=datetime.now(),
        )
        embed.add_field(name="Utilisateur", value=member.mention)
        embed.add_field(name="Staff", value=ctx.author.mention)
        embed.add_field(name="Raison", value=reason, inline=False)
        if send_dm and message_sent:
            embed.add_field(name="Message privé", value="L'utilisateur a été averti.", inline=False)
        elif send_dm:
            embed.add_field(name="Message privé", value="/!\ Aucun message n'a pu être envoyé à l'utilisateur.", inline=False)

        await ctx.send(embed=embed, ephemeral=True)

        guild = GuildWrapper(ctx.guild)
        if not guild.sanctions_log_channel:
            return
        await guild.sanctions_log_channel.send(embed=embed)


    @hybrid_command(name="warnlist")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def warnlist(self, ctx, member: Optional[discord.Member]) -> None:
        """
        Liste les sanctions reçues par un membre.

        Parameters
        ----------
        member : Optional[discord.Member]
            Le membre dont on veut lister les sanctions.
        """
        if member:
            request = select(SanctionModel).where(
                SanctionModel.to_id == member.id,
                SanctionModel.guild_id == ctx.guild.id,
                SanctionModel.type == "warn",
            )
            title = f"Liste des avertissements de {member.name}"
        else:
            request = select(SanctionModel).where(
                SanctionModel.guild_id == ctx.guild.id, SanctionModel.type == "warn"
            )
            title = "Liste des avertissements du serveur"

        sanctions = database.execute(request).scalars().all()
        content = f"**Nombre d'avertissements :** {len(sanctions)}\n\n"

        for sanction in sanctions:
            content += f"**{sanction.id}** ━ Le {sanction.date:%d/%m/%Y à %H:%M}\n"
            if not member:
                to = ctx.guild.get_member(sanction.to_id)
                content += f"> **Membre :** {to.mention}\n"

            by = ctx.guild.get_member(sanction.by_id)
            content += f"> **Modérateur :** {by.mention}\n"
            if sanction.reason:
                content += f"> **Raison :** {sanction.reason}\n"
            content += "\n"

        embed = discord.Embed(
            title=title, description=content, colour=0xFF00FF, timestamp=datetime.now()
        )
        await ctx.send(embed=embed)

    @hybrid_command(name="unwarn")
    @guild_only()
    @has_permissions(manage_messages=True)
    async def unwarn(self, ctx, id: int) -> None:
        """
        Supprime un avertissement.

        Parameters
        ----------
        id : int
            L'identifiant de l'avertissement à supprimer.
        """
        database.execute(delete(SanctionModel).where(SanctionModel.id == id))
        message = f"L'avertissement {id} a été supprimé."
        await ctx.send(message)
        guild = GuildWrapper(ctx.guild)
        if not guild.sanctions_log_channel:
            return
        await guild.sanctions_log_channel.send(message)

    @Cog.listener("on_member_ban")
    async def log_ban(self, guild, user) -> None:
        """
        Stocke le nom de l'utilisateur banni
        """
        self.users[user.id] = user.name

    @Cog.listener("on_member_unban")
    async def log_unban(self, guild, user) -> None:
        """
        Stocke le nom de l'utilisateur débanni
        """
        self.users[user.id] = user.name

    @Cog.listener("on_audit_log_entry_create")
    @guild_only()
    async def log_sanctions(self, entry) -> None:
        """
        Logue les sanctions envers les utilisateurs.

        Parameters
        ----------
        entry : LogActionEntry
            Entrée ajoutée dans le journal des actions du serveur.
        """
        guild = GuildWrapper(entry.guild)
        if not guild.sanctions_log_channel:
            return

        async def handle_log(title, colour, fields):
            """
            Envoie un embed dans le salon de logs des sanctions.

            Parameters
            ----------
            title : str
                Titre de l'embed.
            colour: int
                Couleur de l'embed.
            fields: Callable[discord.Embed, None]
                Fonction permettant d'ajouter des `fields` à l'embed.
            """
            embed = discord.Embed(
                title=title,
                colour=colour,
                timestamp=datetime.now(),
            )
            fields(embed)
            await guild.sanctions_log_channel.send(embed=embed)


        async def handle_log_ban(user, staff, reason):
            """
            Logue le banissement d'un utilisateur dans le salon des logs de sanctions.

            Parameters
            ----------
            user : Any
                Utilisateur cible.
            staff: discord.Member
                Utilisateur initateur de l'action.
            reason: str
                Raison du bannissement.
            """
            # Le nom ne peut être récupéré de `user` si la personne n'est plus sur le serveur.
            user_name = self.users[user.id]
            del self.users[user.id]
            def embed_fields(embed):
                """
                Ajoute les champs nécessaires à l'embed d'un bannissement.

                Parameters
                ----------
                embed : discord.Embed
                    Embed à modifier.
                """
                embed.add_field(name="Utilisateur", value=f"<@{user.id}>")
                embed.add_field(name="Staff", value=staff.mention)
                embed.add_field(name="Raison", value=reason, inline=False)
            await handle_log(f"{user_name} a été banni", 0xFF0000, embed_fields)

        async def handle_log_unban(user, staff):
            """
            Logue le débanissement d'un utilisateur dans le salon des logs de sanctions.

            Parameters
            ----------
            user : Any
                Utilisateur cible.
            staff: discord.Member
                Utilisateur initateur de l'action.
            """
            # Le nom ne peut être récupéré de `user` si la personne n'est plus sur le serveur.
            user_name = self.users[user.id]
            del self.users[user.id]
            def embed_fields(embed):
                """
                Ajoute les champs nécessaires à l'embed d'un débannissement.

                Parameters
                ----------
                embed : discord.Embed
                    Embed à modifier.
                """
                embed.add_field(name="Utilisateur", value=f"<@{user.id}>")
                embed.add_field(name="Staff", value=staff.mention)
            await handle_log(f"{user_name} a été débanni", 0xFA9C1B, embed_fields)

        async def handle_log_to(user, staff, reason, time):
            """
            Logue le time out d'un utilisateur dans le salon des logs de sanctions.

            Parameters
            ----------
            user : Any
                Utilisateur cible.
            staff: discord.Member
                Utilisateur initateur de l'action.
            reason: str
                Raison du time out.
            time: int
                Timestamp de fin de sanction.
            """
            dm_sent = False
            try:
                await user.send(f"Vous avez été TO jusqu'à <t:{time}:F> pour la raison : \n>>> {reason}")
                dm_sent = True
            except:
                dm_sent = False
            def embed_fields(embed):
                """
                Ajoute les champs nécessaires à l'embed d'un time out.

                Parameters
                ----------
                embed : discord.Embed
                    Embed à modifier.
                """
                embed.add_field(name="Utilisateur", value=f"<@{user.id}>")
                embed.add_field(name="Staff", value=staff.mention)
                embed.add_field(name="Timestamp", value=f"<t:{time}:F>", inline=False)
                if dm_sent:
                    embed.add_field(name="Message Privé", value="Envoyé")
                else:
                    embed.add_field(name="Message Privé", value="Non envoyé")
                embed.add_field(name="Raison", value=reason, inline=False)
            await handle_log(f"{user} a été TO",
                0xFDAC5B,
                embed_fields
                )

        async def handle_log_unto(user, staff):
            """
            Logue la révocation d'un time out d'un utilisateur dans le salon des logs de sanctions.

            Parameters
            ----------
            user : Any
                Utilisateur cible.
            staff: discord.Member
                Utilisateur initateur de l'action.
            """
            def embed_fields(embed):
                """
                Ajoute les champs nécessaires à l'embed de la révocation d'un time out.

                Parameters
                ----------
                embed : discord.Embed
                    Embed à modifier.
                """
                embed.add_field(name="Utilisateur", value=f"<@{user.id}>")
                embed.add_field(name="Staff", value=staff.mention)
            await handle_log(f"{user.name} n'est plus TO", 0xFA9C1B, embed_fields)

        action = f"{entry.action}"
        if action == "AuditLogAction.ban":
            await handle_log_ban(entry.target, entry.user, entry.reason)

        elif action == "AuditLogAction.unban":
            await handle_log_unban(entry.target, entry.user)

        # Doit être étrangement avant la condition de TO sinon ne s'applique pas
        elif action == "AuditLogAction.member_update" and (entry.before.timed_out_until and not entry.after.timed_out_until):
            await handle_log_unto(
                entry.target,
                entry.user
            )

        elif action == "AuditLogAction.member_update" and (not entry.before.timed_out_until and entry.after.timed_out_until or entry.before.timed_out_until and entry.before.timed_out_until < entry.after.timed_out_until):
            await handle_log_to(
                entry.target,
                entry.user,
                entry.reason,
                int(entry.after.timed_out_until.timestamp() + 60) # +60 indique la minute qui suit, mieux vaut large que pas assez
            )



async def setup(bot) -> None:
    await bot.add_cog(Sanction(bot))
