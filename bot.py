import discord
from discord.ext import commands, tasks
from scraper import check_for_new_spoilers, mark_as_posted
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not spoiler_checker.is_running():
        spoiler_checker.start()


@tasks.loop(minutes=30)
async def spoiler_checker():
    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("Could not find channel.")
        return

    new_images = check_for_new_spoilers()

    if not new_images:
        print("No new spoilers found.")
        return

    for card_id,card_name, image_path in new_images:
        try:
            await channel.send(
                content=f"**{card_name}**",
                file=discord.File(image_path)
            )

            mark_as_posted(card_id)
            print(f"Posted: {card_name}")
        except Exception as error:
            print(f"Failed to post {card_id}: {error}")


@bot.command()
async def check(ctx):
    await ctx.send("Checking for new spoilers...")

    new_images = check_for_new_spoilers()

    if not new_images:
        await ctx.send("No new spoilers found.")
        return

    for image_url, image_path in new_images:
        try:
            await ctx.send(file=discord.File(image_path))
            mark_as_posted(image_url)
        except Exception as error:
            await ctx.send(f"Failed to post one image: {error}")

    await ctx.send(f"Posted {len(new_images)} new spoilers.")


bot.run(TOKEN)