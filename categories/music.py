import discord
from discord.ext import commands, menus
import wavelink

import datetime as dt
import asyncio
import typing
import re

import utilities.facility as Facility
from utilities.converters import IntervalConverter
from templates.navigate import Pages

URL_REG = re.compile(r'https?://(?:www\.)?.+')

class Track(wavelink.Track):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")

class MusicController:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.channel = None

        self.next = asyncio.Event()
        self.queue = asyncio.Queue()

        self.volume = 50

        self.is_single_loop = False
        self.is_queue_loop = False
        self.current_track : Track = None

        self.player : wavelink.Player = self.bot.wavelink.get_player(self.guild_id)
        self.menu = InteractiveMenu()

        self.bot.loop.create_task(self.controller_loop())

    async def controller_loop(self):
        await self.bot.wait_until_ready()

        #self.player = self.bot.wavelink.get_player(self.guild_id)
        await self.player.set_volume(self.volume)

        while True:
            self.next.clear()

            if not self.is_single_loop:
                self.current_track = await self.queue.get()
            
            await self.player.play(self.current_track)
            await self.channel.send(f"Now playing: `{self.current_track}`")
            if self.menu.message is not None:
                await self.menu.update_menu(self)

            # Blocking await till the song is completed.
            await self.next.wait()
            if self.is_queue_loop:
                await self.queue.put(self.current_track)

class InteractiveMenu(menus.Menu):
    def __init__(self):
        super().__init__(timeout = None)
    
    async def send_initial_message(self, ctx, channel):
        embed = discord.Embed(title = "Placeholder")
        return await ctx.send(embed = embed)
    
    def update_context(self, payload):
        import copy
        ctx = copy.copy(self.ctx)
        ctx.author = payload.member
        return ctx

    async def update_menu(self, controller : MusicController):
        current_track = controller.current_track

        embed = discord.Embed(
            title = "Music Controller",
            description = "",
            color = discord.Color.green()
        ).add_field(
            name = "Duration:",
            value = str(dt.timedelta(milliseconds = current_track.duration))
        ).add_field(
            name = "Video URL:",
            value = f"[Click here!]({current_track.uri})"
        ).add_field(
            name = "Requested By:",
            value = current_track.requester.name
        ).add_field(
            name = "Queue Length:",
            value = controller.queue.qsize()
        ).add_field(
            name = "Volume:",
            value = f"**{controller.player.volume}**",
        )
        
        if current_track.thumb is not None:
            embed.set_thumbnail(
            url = current_track.thumb
        )

        if controller.queue.empty():
            embed.add_field(
                name = "Coming Up:",
                value = "**-** `None`",
                inline = False
            )
        else:
            upcoming = list(controller.queue._queue)
            embed.add_field(
                name = "Coming Up:",
                value = f"**-** `{upcoming[0].title}`",
                inline = False
            )
        
        embed.description = f"Now Playing: **{current_track.title}**"
        
        await self.message.edit(embed = embed)
    
    @menus.button('⏸')
    async def on_pause_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('pause')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
    @menus.button('⏩')
    async def on_skip_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('skip')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
    @menus.button('🔀')
    async def on_shuffle_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('queue shuffle')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
    @menus.button('🔁')
    async def on_qloop_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('queue loop')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
    @menus.button('🔂')
    async def on_loop_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('repeat')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
    @menus.button('⏹')
    async def on_stop_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('stop')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
        await self.message.delete()
        self.message = None
        self.stop()
    @menus.button('❌')
    async def on_disconnect_button(self, payload):
        ctx = self.update_context(payload)
        ctx.command = self.bot.get_command('disconnect')
        await self.bot.invoke(ctx)
        ctx.command.reset_cooldown(ctx)
        await self.message.delete()
        self.message = None
        self.stop()

class Music(commands.Cog, command_attrs = {"cooldown_after_parsing" : True}):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = '🎵'

        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot = self.bot)
        self.controllers : typing.Dict[MusicController] = {}
        
        self.bot.loop.create_task(self.start_nodes())
    
    async def start_nodes(self):
        await self.bot.wait_until_ready()

        # Initiate our nodes. For this example we will use one server.
        # Region should be a discord.py guild.region e.g sydney or us_central (Though this is not technically required)
        node = await self.bot.wavelink.initiate_node(host='0.0.0.0',
                                                     port=2333,
                                                     rest_uri='http://0.0.0.0:2333',
                                                     password='youshallnotpass',
                                                     identifier='TEST',
                                                     region='us_west')

        # Set our node hook callback
        node.set_hook(self.on_event_hook)
    
    def cog_unload(self):
        # Clear all controllers, as they're now invalid.
        self.controllers = {}
        return super().cog_unload()
    
    async def cog_check(self, ctx : commands.Context):
        if isinstance(ctx.channel, discord.DMChannel):
            raise commands.NoPrivateMessage()
        
        return True

    async def on_event_hook(self, event):
        """Node hook callback."""
        if isinstance(event, (wavelink.TrackEnd, wavelink.TrackException)):
            controller = self.get_controller(event.player)
            controller.next.set()
        
    def get_controller(self, value: typing.Union[commands.Context, wavelink.Player]) -> MusicController:
        if isinstance(value, commands.Context):
            gid = value.guild.id
        else:
            gid = value.guild_id
        
        if self.controllers.get(gid) is None:
            self.controllers[gid] = MusicController(self.bot, gid)

        return self.controllers[gid]

    @commands.command(aliases = ['join'])
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.bot_has_guild_permissions(connect = True, speak = True)
    @commands.cooldown(rate = 1, per = 2.0, type = commands.BucketType.guild)
    async def connect(self, ctx, *, voice_channel : discord.VoiceChannel = None):
        '''
        Connect to a voice channel.
        If it is not provided, it'll connect to the VC you're in.

        **Aliases:** `join`.
        **Usage:** {usage}
        **Cooldown:** 2 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} discord got talents

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        if voice_channel is None:
            try:
                voice_channel = ctx.author.voice.channel
            except AttributeError:
                await ctx.reply("No channel to join. Please either specify the channel or join one.")
                return
        
        controller = self.get_controller(ctx)
        controller.channel = ctx.channel
        await ctx.reply(f"Connecting to `{voice_channel}`...", mention_author = False)
        await controller.player.connect(voice_channel.id)
    
    @commands.command(aliases = ['dc'])
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def disconnect(self, ctx):
        '''
        Disconnect the player from the VC.
        This will forget any configurations on the player, including loop, queue, volume, etc.

        **Aliases:** `dc`.
        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        await controller.player.stop()
        while not controller.queue.empty():
            await controller.queue.get()
        
        await controller.player.disconnect()
        self.controllers.pop(ctx.guild.id)
        await ctx.reply("**Successfully disconnected.**", mention_author = False)

    @commands.command(aliases = ['np'])
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def now_playing(self, ctx):
        '''
        Display the current playing song.

        **Aliases:** `np`
        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}np

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            return await ctx.reply("There's nothing playing.")
        
        ratio = float(controller.player.position) / float(controller.current_track.duration)
        # Milliseconds have this format hh:mm:ss.somerandomstuffs, so just split at the first dot.
        current_position = str(dt.timedelta(milliseconds = controller.player.position)).split('.')[0]
        full_duration = str(dt.timedelta(milliseconds = controller.current_track.duration)).split('.')[0]
        # We're using c-string here because when the dot is at the beginning and the end,
        # I need to deal with some weird string concat, so no.
        progress_cstring = ['-'] * 30

        # [30, -1) to make sure the dot can appear as the first character
        for i in range(30, -1, -1):
            if i / 30.0 <= ratio:
                progress_cstring[i] = '🔘'
                break
        
        progress_string = ''.join(progress_cstring)

        embed = Facility.get_default_embed(
            title = "Now Playing",
            description = f"""
                [{controller.current_track.title}]({controller.current_track.uri})

                `{progress_string}`

                `{current_position}` / `{full_duration}`

                **Requested by:** `{ctx.author}`
            """,
            author = ctx.author
        ).set_thumbnail(
            url = controller.current_track.thumb
        )

        await ctx.reply(embed = embed, mention_author = False)

    @commands.command(aliases = ['p'])
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 1.0, type = commands.BucketType.guild)
    async def play(self, ctx, *, track):
        '''
        Play a song from YouTube, SoundCloud, Twitch, Vimeo, and Mixer.
        You can provide a link or the song's title/keywords. You can also use a playlist link.

        **Aliases:** `p`.
        **Usage:** {usage}
        **Cooldown:** 1 second per 1 use (guild)
        **Example 1:** {prefix}{command_name} https://www.youtube.com/watch?v=dQw4w9WgXcQ
        **Example 2:** {prefix}{command_name} show yourself

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_connected:
            await ctx.invoke(self.connect)
        if ctx.author.voice is None:
            return

        if not URL_REG.match(track):
            track = f'ytsearch:{track}'
        tracks = await self.bot.wavelink.get_tracks(track)

        if tracks is None:
            await ctx.reply("Could not find any songs.")
            return
        
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester = ctx.author)
                await controller.queue.put(track)
            await ctx.reply(f"Added the playlist {tracks.data['playlistInfo']['name']} with {len(tracks.tracks)} songs to the queue.", mention_author = False, delete_after = 5)
        else:
            track = Track(tracks[0].id, tracks[0].info, requester = ctx.author)
            await controller.queue.put(track)
            await ctx.reply(f"Added {tracks[0]} to the queue.", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)
    
    @commands.command()
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 1.0, type = commands.BucketType.guild)
    async def pause(self, ctx):
        '''
        Toggle pausing the player.

        **Usage:** {usage}
        **Cooldown:** 1 second per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            await ctx.reply("There's nothing to pause you dummy.", delete_after = 5)
            return
        if controller.player.paused:
            await controller.player.set_pause(False)
            await ctx.reply("Resumed!", mention_author = False, delete_after = 5)
        else:
            await controller.player.set_pause(True)
            await ctx.reply("Paused!", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)

    @commands.command(aliases = ['find'])
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def search(self, ctx, *, track):
        '''
        Search the input track and return 10 relevant results.
        You can then copy the link of the one you want into `play`.

        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} rickroll

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`
        '''

        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{track}')
        if tracks is None:
            await ctx.reply("Could not find any songs.")
            return
        
        embed = Facility.get_default_embed(
            title = "Top 10 search results",
            description = "",
            timestamp = dt.datetime.utcnow(),
            author = ctx.author
        )

        for index, track in enumerate(tracks):
            embed.description += f"**{index + 1}.** [{track.title}]({track.uri}) - {dt.timedelta(milliseconds = track.duration)}\n\n"
            if index == 9:
                break
        
        await ctx.reply(embed = embed, mention_author = False)

    @commands.command()
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def seek(self, ctx, *, position : IntervalConverter):
        '''
        Seek to the provided timestamp.
        If the timestamp exceeds the song's duration, it'll play the next song in queue.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} 3:20

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            return await ctx.reply("There's no song to seek.")
        
        await controller.player.seek(position.seconds * 1000)
        await ctx.reply(f"⏩ **Seek to `{position}`.**", mention_author = False)

    @commands.command()
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def repeat(self, ctx):
        '''
        Toggle single song looping.
        
        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Add Reactions`, `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        controller.is_single_loop = not controller.is_single_loop
        if controller.is_single_loop and not controller.player:
            await ctx.reply("There's nothing to loop.", delete_after = 5)
            controller.is_single_loop = False
            return
        
        if controller.is_single_loop:
            await ctx.reply("🔂 **Enabled!**", mention_author = False, delete_after = 5)
        else:
            await ctx.reply("🔂 **Disabled!**", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)
    
    @commands.group(aliases = ['q'], invoke_without_command = True)
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def queue(self, ctx):
        '''
        Display the song queue.

        **Aliases:** `q`
        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Add Reactions`, `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if controller.queue.empty() and controller.player.is_playing == False:
            embed = Facility.get_default_embed(timestamp = dt.datetime.utcnow())
            embed.description = "*There are no songs currently in queue.*"
            await ctx.reply(embed = embed, mention_author = False)
        elif controller.queue.empty():
            embed = Facility.get_default_embed(
                title = f"Queue for {ctx.guild}",
                timestamp = dt.datetime.utcnow(),
                author = ctx.author
            ).add_field(
                name = "Now playing:",
                value = f"[{controller.current_track.title}]({controller.current_track.uri}) - {dt.timedelta(milliseconds = controller.current_track.duration)}",
                inline = False
            ).add_field(
                name = "Status:",
                value = "- 🔂: " + ('✅' if controller.is_single_loop else '❌') + "\n- 🔁: " + ('✅' if controller.is_queue_loop else '❌'),
                inline = False
            )
            await ctx.reply(embed = embed, mention_author = False)
        else:
            current = controller.current_track
            upcoming = list(controller.queue._queue)

            page = Pages()

            text = ""
            embed = None
            for index, track in enumerate(upcoming):
                if index % 5 == 0:
                    embed = Facility.get_default_embed(
                        title = f"Queue for {ctx.guild}",
                        timestamp = dt.datetime.utcnow(),
                        author = ctx.author
                    ).add_field(
                        name = "Now playing:",
                        value = f"[{current.title}]({current.uri}) - {dt.timedelta(milliseconds = current.duration)}",
                        inline = False
                    )
                
                text += f"`{index + 1}`. [{track.title}]({track.uri}) - {dt.timedelta(milliseconds = track.duration)}\n"

                if index % 5 == 4:
                    embed.add_field(
                        name = "Up Next:",
                        value = text,
                        inline = False
                    ).add_field(
                        name = "Status:",
                        value = "- 🔂: " + ('✅' if controller.is_single_loop else '❌') + "\n- 🔁: " + ('✅' if controller.is_queue_loop else '❌'),
                        inline = False
                    )
                    page.add_page(embed)
                    text = ""
                    embed = None
            if embed is not None:
                embed.add_field(
                    name = "Up Next:",
                    value = text,
                    inline = False
                ).add_field(
                    name = "Status:",
                    value = "- 🔂: " + ('✅' if controller.is_single_loop else '❌') + "\n- 🔁: " + ('✅' if controller.is_queue_loop else '❌'),
                    inline = False
                )
                page.add_page(embed)
            await page.start(ctx)
    
    @queue.command(name = 'clear')
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def queue_clear(self, ctx):
        '''
        Clear queue, but keep the current song playing.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        while not controller.queue.empty():
            await controller.queue.get()
        
        await ctx.reply("Cleared song queue!", mention_author = False)

    @queue.command(name = 'loop')
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def queue_loop(self, ctx):
        '''
        Toggle queue loop.
        This will disable single song loop if it is enabled.

        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Add Reactions`, `Read Message History`, `Send Messages`.
        '''
        controller = self.get_controller(ctx)
        controller.is_queue_loop = not controller.is_queue_loop
        if controller.is_queue_loop and controller.is_single_loop:
            await ctx.invoke(self.repeat)
        
        if controller.is_queue_loop:
            await ctx.reply("🔁 **Enabled!**", mention_author = False, delete_after = 5)
        else:
            await ctx.reply("🔁 **Disabled!**", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)

    @queue.command(name = 'move')
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def queue_move(self, ctx, source_index : int, destination_index : int):
        '''
        Move a song in the queue to a new order index.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} 3 1

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        max_size = controller.queue.qsize()
        source_index -= 1
        destination_index -= 1
        if source_index < 0 or source_index > max_size - 1 or destination_index < 0  or destination_index > max_size - 1:
            return await ctx.reply("Index out of range.")
        
        fake_queue = asyncio.Queue()
        removed_track = None
        for i in range(0, max_size):
            if i == source_index:
                removed_track = await controller.queue.get()
            else:
                await fake_queue.put(await controller.queue.get())
        max_size -= 1
        for i in range(0, max_size):
            await controller.queue.put(await fake_queue.get())
        
        controller.queue._queue.insert(destination_index, removed_track)

        await ctx.reply(f"**Track** `{removed_track.title}` **moved from {source_index + 1} to {destination_index + 1}.**", mention_author = False)

    @queue.command(name = 'remove')
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def queue_remove(self, ctx, index : int):
        '''
        Remove a song from the queue using the order index.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} 3

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        max_size = controller.queue.qsize()
        index -= 1
        if index < 0 or index > max_size - 1:
            await ctx.reply("Index out of range.")
            return
        
        fake_queue = asyncio.Queue()
        removed_track = None
        for i in range(0, max_size):
            if i == index:
                removed_track = await controller.queue.get()
            else:
                await fake_queue.put(await controller.queue.get())
        max_size -= 1
        for i in range(0, max_size):
            await controller.queue.put(await fake_queue.get())
        
        await ctx.reply(f"**Track removed:** `{removed_track.title}`.", mention_author = False)

    @queue.command(name = 'shuffle')
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def queue_shuffle(self, ctx):
        '''
        Shuffle the queue.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Add Reactions`, `Read Message History`, `Send Messages`.
        '''
        controller = self.get_controller(ctx)
        if controller.queue.empty():
            await ctx.reply("There's nothing to shuffle!")
            return
        
        import random
        random.shuffle(controller.queue._queue)
        await ctx.reply("🔀 **Shuffled**!", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)
    
    @commands.command()
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    async def resume(self, ctx):
        '''
        Resume the player from pausing.

        **Usage:** {usage}
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            await ctx.reply("There's nothing to resume from.", delete_after = 5)
            return
        if controller.player.paused:
            await controller.player.set_pause(False)
            await ctx.reply("Resumed!", mention_author = False, delete_after = 5)
        else:
            await ctx.reply("Player is not paused.")
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)
    
    @commands.command(aliases = ['vol'])
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 3.0, type = commands.BucketType.guild)
    async def volume(self, ctx, *, new_volume : int):
        '''
        Adjust the player's volume.
        Acceptable volume range is from 0-200. By default, the player has volume 50.

        **Aliases:** `vol`.
        **Usage:** {usage}
        **Cooldown:** 3 seconds per 1 use (guild)
        **Example:** {prefix}{command_name} 100

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        
        new_volume = max(min(new_volume, 200), 0)
        controller.volume = new_volume

        await controller.player.set_volume(new_volume)
        await ctx.reply(f"Set volume to {new_volume}.", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)

    @commands.command(aliases = ['s'])
    @commands.bot_has_permissions(add_reactions = True, read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def skip(self, ctx):
        '''
        Skip the current song.
        If single loop is enabled, the next song will be the same.

        **Usage:** {usage}
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Add Reactions`, `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            await ctx.reply("There are no songs to skip.")
            return
        
        await controller.player.stop()
        await ctx.reply("Skipped!", mention_author = False, delete_after = 5)
        if controller.menu.message is None:
            await controller.menu.start(ctx)
            await controller.menu.update_menu(controller)
        else:
            await controller.menu.update_menu(controller)

    @commands.command()
    @commands.bot_has_permissions(read_message_history = True, send_messages = True)
    @commands.cooldown(rate = 1, per = 5.0, type = commands.BucketType.guild)
    async def stop(self, ctx):
        '''
        Stop the player and clear the queue.
        This will stop the song, disable all loops, clear all songs in queue, but retains the volume.

        **Usage:** {usage}
        **Cooldown:** 5 seconds per 1 use (guild)
        **Example:** {prefix}{command_name}

        **You need:** None.
        **I need:** `Read Message History`, `Send Messages`.
        '''

        controller = self.get_controller(ctx)
        if not controller.player.is_playing:
            await ctx.reply("There's nothing to stop.")
            return
        
        await controller.player.stop()
        controller.is_queue_loop = False
        controller.is_single_loop = False
        # Clear queue
        while not controller.queue.empty():
            await controller.queue.get()
        
        await ctx.reply("Stopped the player.", mention_author = False)
    
def setup(bot):
    bot.add_cog(Music(bot))