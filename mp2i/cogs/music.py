from collections import defaultdict

import discord
import youtube_dl
from discord.ext.commands import Cog, hybrid_command, guild_only, check

from mp2i.utils import youtube

ytdl = youtube_dl.YoutubeDL()


def is_in_voice_channel(ctx):
    if ctx.author.voice and ctx.voice_client:
        return ctx.author.voice.channel == ctx.voice_client.channel
    return False


class Video:
    """
    Represents a video with stream url and name extracted by youtube_dl
    """

    def __init__(self, name: str, url: str):
        video = ytdl.extract_info(url, download=False)
        video_format = video["formats"][0]
        self.url = url
        self.name = name
        self.stream_url = video_format["url"]


class Music(Cog):
    """
    Offers an interface with typical commands to play music in voice channel
    """

    def __init__(self, bot):
        self.bot = bot
        self.musics = defaultdict(list)

    @hybrid_command(name="play", aliases=["p"])
    @guild_only()
    async def play(self, ctx, *, query: str) -> None:
        """
        Joue la musique correspondante à la recherche.

        Parameters
        ----------
        query : str
            Mots clés de la musique.
        """
        voice_client = ctx.voice_client
        try:
            v_infos = next(youtube.search(query, n=1))
        except StopIteration:
            await ctx.send("Aucune musique n'a été trouvée.")
            return

        if voice_client and voice_client.is_playing():
            video = Video(**v_infos)
            self.musics[ctx.guild].append(video)
            await ctx.send(
                f"Musique ajoutée à la file d'attente: **{video.name}**\n"
                f"{video.url}"
            )
        elif ctx.author.voice:
            if not voice_client:
                voice_client = await ctx.author.voice.channel.connect()
            video = Video(**v_infos)
            self.play_song(voice_client, self.musics[ctx.guild], video)
            await ctx.send(f"Musique en cours: **{video.name}** \n{video.url}")
        else:
            await ctx.send("Vous n'êtes pas connecté à un salon vocal")

    def play_song(self, voice_client, queue: list, video: Video) -> None:
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                source=video.stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1",
            )
        )

        def next_song(_):
            if len(queue) > 0:
                new_song = queue.pop(0)
                self.play_song(voice_client, queue, new_song)

        voice_client.play(source, after=next_song)

    @hybrid_command()
    @guild_only()
    @check(is_in_voice_channel)
    async def skip(self, ctx) -> None:
        """
        Passer à la musique suivante, si disponible.
        """
        ctx.voice_client.stop()
        if len(self.musics[ctx.guild]) > 0:
            video = self.musics[ctx.guild][0]
            await ctx.send(f"Musique en cours: **{video.name}** \n{video.url}")
        else:
            await ctx.send("Aucune musique en cours")

    @hybrid_command()
    @guild_only()
    @check(is_in_voice_channel)
    async def pause(self, ctx) -> None:
        """
        Mettre en pause la musique en cours.
        """
        if not ctx.voice_client.is_paused():
            ctx.voice_client.pause()

    @hybrid_command()
    @guild_only()
    @check(is_in_voice_channel)
    async def resume(self, ctx) -> None:
        """
        Reprendre la musique en cours.
        """
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()

    @hybrid_command(aliases=["quit"])
    @guild_only()
    @check(is_in_voice_channel)
    async def leave(self, ctx) -> None:
        """
        Arrêter la musique et la file d'attente.
        """
        await ctx.voice_client.disconnect(force=True)
        self.musics[ctx.guild] = []


async def setup(bot) -> None:
    await bot.add_cog(Music(bot))
