import discord
from discord.ext import commands
import os

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")


# Example commands
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command()
async def info(ctx):
    await ctx.send("I am a Discord bot controlled via a dashboard!")


# Dynamically load commands
@bot.command()
async def load(ctx, extension):
    try:
        bot.load_extension(f"commands.{extension}")
        await ctx.send(f"Loaded {extension} successfully!")
    except Exception as e:
        await ctx.send(f"Failed to load {extension}: {e}")


@bot.command()
async def unload(ctx, extension):
    try:
        bot.unload_extension(f"commands.{extension}")
        await ctx.send(f"Unloaded {extension} successfully!")
    except Exception as e:
        await ctx.send(f"Failed to unload {extension}: {e}")
