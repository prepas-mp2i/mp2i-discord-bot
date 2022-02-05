import asyncio

import discord
import youtube_dl
from discord.ext.commands import Cog, command, guild_only

from .utils import youtube

ytdl = youtube_dl.YoutubeDL()


class Video:
    """
    Represents a video with stream url and name extracted by youtube_dl
    """

    def __init__(self, name, url):
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
        self.musics = {}

    @command(name="play", aliases=["p"])
    @guild_only()
    async def play(self, ctx, *params):
        """
        Joue la musique correspondante à la recherche
        """
        voice_client = ctx.guild.voice_client
        query = " ".join(params)
        try:
            v_infos = next(youtube.search(query, n=1))
        except StopIteration:
            await ctx.send("Aucune musique n'a été trouvée.")
            return

        if voice_client and voice_client.channel:
            # if client is already connected
            video = Video(**v_infos)
            self.musics[ctx.guild].append(video)
            await ctx.send(f"Musique ajoutée à la file d'attente: **{video.name}**")
        elif ctx.author.voice:
            voice_channel = ctx.author.voice.channel
            video = Video(**v_infos)
            self.musics[ctx.guild] = []
            voice_client = await voice_channel.connect()
            self.play_song(voice_client, self.musics[ctx.guild], video)

            await ctx.send(f"Musique en cours: **{video.name}** \n{video.url}")
        else:
            await ctx.send("Vous n'êtes pas connecté à un salon vocal")

    def play_song(self, voice_client, queue, song):
        """
        Coroutine to play a song
        """
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                song.stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1",
            )
        )

        def next_song(_):
            if len(queue) > 0:
                new_song = queue.pop(0)
                self.play_song(voice_client, queue, new_song)
            else:
                try:
                    asyncio.run_coroutine_threadsafe(
                        voice_client.disconnect, self.bot.loop
                    )
                except TypeError:
                    pass

        voice_client.play(source, after=next_song)

    @command()
    @guild_only()
    async def skip(self, ctx):
        """
        Passer à la musique suivante, si disponible
        """
        voice_client = ctx.guild.voice_client
        try:
            voice_client.stop()
        except TypeError:
            pass
        else:
            video = self.musics[ctx.guild][0]
            await ctx.send(f"Morceau en cours: **{video.name}** \n{video.url}")

    @command()
    @guild_only()
    async def pause(self, ctx):
        voice_client = ctx.guild.voice_client
        if not voice_client.is_paused():
            voice_client.pause()

    @command()
    @guild_only()
    async def resume(self, ctx):
        voice_client = ctx.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()

    @command(aliases=["quit"])
    @guild_only()
    async def leave(self, ctx):
        """
        Arrêter la musique et la queue
        """
        voice_client = ctx.guild.voice_client
        await voice_client.disconnect()
        self.musics[ctx.guild] = []


def setup(bot):
    bot.add_cog(Music(bot))
