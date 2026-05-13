import os
import json
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from web_scraper.scraper import SpoilerScraper
from gemini import Gemini

class OkupljanjeBot(commands.Bot):
    def __init__(self):
        load_dotenv()

        self.config = self.load_config()

        self.token = os.getenv("DISCORD_TOKEN")
        self.new_card_channel_id = self.config.get("new_card_channel_id")
        self.ai_channel_id = self.config.get("ai_channel_id")


        intents = discord.Intents.default()
        intents.message_content = True
        self.scraper = SpoilerScraper()
        self.gemini = Gemini()

        super().__init__(command_prefix="!", intents=intents)


    def load_config(self):
        if not os.path.exists("saved_channels.json"):
            return {}
        with open("saved_channels.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self):
        with open("saved_channels.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

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

        @commands.command(name="rulling")
        async def rulling_command(ctx,*,message):
            await self.rules_question(ctx, message=message)

        self.add_command(check_command)
        self.add_command(set_channel_command)
        self.add_command(rulling_command)

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
        response = self.gemini.rullings_question(message)
        await ctx.send(response)


    async def setchannel(self, ctx, channel_type: str):
        if channel_type == "new_cards":
            self.new_card_channel_id = ctx.channel.id
            self.config["new_card_channel_id"] = self.new_card_channel_id
        elif channel_type == "ai":
            self.ai_channel_id = ctx.channel.id
            self.config["ai_channel_id"] = self.ai_channel_id
        else:
            await ctx.send("Invalid channel type")
            return

        self.save_config()

        await ctx.send(f"Channel {channel_type} for channel set to {ctx.channel.mention}")
