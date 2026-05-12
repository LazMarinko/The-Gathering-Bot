import os
import json
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from web_scraper.scraper import SpoilerScraper


class OkupljanjeBot(commands.Bot):
    def __init__(self):
        load_dotenv()

        self.config = self.load_config()

        self.token = os.getenv("DISCORD_TOKEN")
        self.channel_id = self.config.get("new_card_channel_id")


        intents = discord.Intents.default()
        intents.message_content = True
        self.scraper = SpoilerScraper()

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

        @commands.command(name="setnewcardchannel")
        async def set_channel_command(ctx):
            await self.setnewcardchannel(ctx)

        self.add_command(check_command)
        self.add_command(set_channel_command)

    @tasks.loop(minutes=30)
    async def spoiler_checker(self):
        if self.channel_id is None:
            print("No new card channel set")
            return

        channel = self.get_channel(self.channel_id)

        if channel is None:
            channel = await self.fetch_channel(self.channel_id)

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


    async def setnewcardchannel(self, ctx):
        self.channel_id = ctx.channel.id
        self.config["new_card_channel_id"] = self.channel_id
        self.save_config()

        await ctx.send(f"New card channel set to {ctx.channel.mention}")
