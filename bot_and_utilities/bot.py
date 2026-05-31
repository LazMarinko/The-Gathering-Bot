import asyncio
import os
import json
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google.genai.errors import ServerError

from web_scraper.scraper import SpoilerScraper
from ai.ruling_question import RulingQuestion
from ai.deck_cut import DeckCut
import io

class OkupljanjeBot(commands.Bot):
    def __init__(self):
        load_dotenv()

        self.config = self.load_config()

        self.token = os.getenv("DISCORD_TOKEN")
        self.new_card_channel_id = self.config.get("new_card_channel_id")
        self.ruling_channel_id = self.config.get("ruling_channel_id")
        self.deckcut_channel_id = self.config.get("deckcut_channel_id")

        intents = discord.Intents.default()
        intents.message_content = True
        self.scraper = SpoilerScraper()
        self.ruling = RulingQuestion()
        self.deckcut_ai = DeckCut()

        super().__init__(command_prefix="!", intents=intents, help_command=None)


    def load_config(self):
        if not os.path.exists("saved_channels.json"):
            return {}
        with open("saved_channels.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self):
        with open("saved_channels.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    async def wrong_channel(self, ctx, channel_id):
        await ctx.send(
            f"Please use this command in <#{channel_id}>."
        )

    async def on_ready(self):
        print(f"Logged in as {self.user}")

        if not self.spoiler_checker.is_running():
            self.spoiler_checker.start()

    async def setup_hook(self):
        @commands.command(name="check")
        async def check_command(ctx):
            await self.check(ctx)

        @commands.command(name="setchannel")
        async def set_channel_command(ctx, channel_type: str):
            await self.setchannel(ctx, channel_type)

        @commands.command(name="ruling")
        async def rulling_command(ctx,*,message):
            await self.rules_question(ctx, message=message)
        @commands.command(name="deckcut")
        async def deckcut_command(ctx,*,message):
            await self.deckcut(ctx, message=message)
        @commands.command(name="help")
        async def help_command(ctx,*,message=None):
            await self.help(ctx, message=message)

        self.add_command(check_command)
        self.add_command(set_channel_command)
        self.add_command(rulling_command)
        self.add_command(deckcut_command)
        self.add_command(help_command)

    @tasks.loop(minutes=30)
    async def spoiler_checker(self):
        if self.new_card_channel_id is None:
            print("No new card channel set")
            return
        try:
            channel = self.get_channel(int(self.new_card_channel_id))

            if channel is None:
                channel = await self.fetch_channel(int(self.new_card_channel_id))

        except discord.NotFound:
            print(f"Unknown channel: {self.new_card_channel_id}. Run !setchannel cards again.")
            return

        except discord.Forbidden:
            print(f"No permission to access channel: {self.new_card_channel_id}")
            return

        await self.post_new_spoilers(channel)

    @spoiler_checker.before_loop
    async def before_spoiler_checker(self):
        await self.wait_until_ready()

    async def post_new_spoilers(self, channel):
        new_images = self.scraper.check_for_new_spoilers()

        if not new_images:
            print("No new spoilers found.")
            return

        for card_id, card_name, image_path in new_images:
            try:
                await channel.send(
                    content=f"**{card_name}**",
                    file=discord.File(image_path)
                )

                self.scraper.mark_as_posted(card_id)
                print(f"Posted: {card_name}")

            except Exception as error:
                print(f"Failed to post {card_name}: {error}")

    async def check(self, ctx):
        await ctx.send("Checking for new spoilers...")

        new_images = self.scraper.check_for_new_spoilers()

        if not new_images:
            await ctx.send("No new spoilers found.")
            return

        for card_id, card_name, image_path in new_images:
            try:
                await ctx.send(
                    content=f"**{card_name}**",
                    file=discord.File(image_path)
                )

                self.scraper.mark_as_posted(card_id)

            except Exception as error:
                await ctx.send(f"Failed to post {card_name}: {error}")

        await ctx.send(f"Posted {len(new_images)} new spoilers.")


    async def rules_question(self, ctx, *, message):
        if ctx.channel.id != self.ruling_channel_id:
            await self.wrong_channel(ctx, self.ruling_channel_id)
            return

        try:
            response = self.ruling.rulings_question(message)
            await ctx.send(response)
        except ServerError:
            await ctx.send("Server error please try again later")

    async def send_text_file(self, ctx, text, filename="deck_cuts.txt"):
        file = discord.File(
            fp = io.BytesIO(text.encode("utf-8")),
            filename=filename
        )
        await ctx.send(
            content = "Here is the list with the cuts",
            file = file
        )

    async def deckcut(self, ctx, *, message):
        if ctx.channel.id != self.deckcut_channel_id:
            await self.wrong_channel(ctx, self.deckcut_channel_id)
            return

        await ctx.send(
            "Now send the decklist"
        )

        def check(reply):
            return(
                reply.author == ctx.author
                and reply.channel == ctx.channel
                and len(reply.attachments) > 0
            )

        try:
            reply = await self.wait_for(
                "message",
                check=check,
                timeout=120
            )
        except asyncio.TimeoutError:
            await ctx.send("Timed out.")
            return

        attachment = reply.attachments[0]

        if not attachment.filename.endswith(".txt"):
            await ctx.send("Pleae upload a .txt file.")
            return

        file_bytes = await attachment.read()
        decklist = file_bytes.decode("utf-8")

        def count_deck_cards(decklist_text):
            count = 0

            for line in decklist_text.splitlines():
                line = line.strip()

                if not line:
                    continue

                parts = line.split(" ", 1)

                if parts[0].isdigit():
                    count += int(parts[0])
                else:
                    count += 1

            return count

        deck_count = count_deck_cards(decklist)
        cards_to_cut = deck_count - 99

        full_prompt = f"""
            Commander + Tags:
            {message}
            
            Decklist:
            {decklist}
            
            Cards to cut:
            {cards_to_cut}
        """
        try:
            response = await asyncio.to_thread(
                self.deckcut_ai.deckcut,
                full_prompt
            )
        except ServerError:
            await ctx.send("Server error please try again later")
            return
        await self.send_text_file(ctx, response)


    async def setchannel(self, ctx, channel_type: str):
        if channel_type == "new_cards":
            self.new_card_channel_id = ctx.channel.id
            self.config["new_card_channel_id"] = self.new_card_channel_id
        elif channel_type == "ruling":
            self.ruling_channel_id = ctx.channel.id
            self.config["ruling_channel_id"] = self.ruling_channel_id
        elif channel_type == "deckcut":
            self.deckcut_channel_id = ctx.channel.id
            self.config["deckcut_channel_id"] = self.deckcut_channel_id
        else:
            await ctx.send("Invalid channel type")
            return

        self.save_config()

        await ctx.send(f"Channel {channel_type} for channel set to {ctx.channel.mention}")


    async def help(self, ctx, *, message = None):
        if message is None:
            await ctx.send(
                "List of commands:\n"
                "!ruling\n"
                "!setchannel\n"
                "!deckcut\n\n"
                "For more information use:\n"
                "`!help ruling`\n"
                "`!help setchannel`\n"
                "`!help deckcut`"
            )
            return
        if "ruling" in message:
            await ctx.send(
                "`!ruling` must be followed by a Magic: The Gathering ruling question.\n"
                "When searching for a card put the card name in []"
                "Example: `!ruling Can I counter [Last March of the Ents]?`"
            )
        elif "setchannel" in message:
            await ctx.send(
                "`!setchannel` sets the current channel for one of the bot's features.\n\n"
                "Available channel types:\n"
                "- `new_cards` → Channel for automatic new card spoiler posts\n"
                "- `ruling` → Channel for MTG ruling questions\n"
                "- `deckcut` → Channel for AI deck cutting requests\n\n"
                "Examples:\n"
                "`!setchannel new_cards`\n"
                "`!setchannel ruling`\n"
                "`!setchannel deckcut`"
            )
        elif "deckcut" in message:
            await ctx.send(
                "`!deckcut` trims a Commander decklist down to the legal size using AI.\n\n"
                "Usage:\n"
                "`!deckcut Commander Name Tags(optional)`\n\n"
                "After running the command, upload the decklist as a `.txt` file.\n\n"
                "Examples:\n"
                "`!deckcut Atraxa poison`\n"
                "`!deckcut Yurlok group slug`\n"
                "`!deckcut Loot blink`\n\n"
                "The bot will analyze the deck, determine the required cuts, "
                "and return the updated decklist."
            )
        else:
            await ctx.send(
                "Sent message contains no known commands."
            )