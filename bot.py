import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_USERS = os.getenv("ADMIN_USERS").split(",")  # Comma-separated admin IDs

# Intents and bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Check if a user is an admin
def is_admin(ctx):
    return str(ctx.author.id) in ADMIN_USERS

# Bot events
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}.")
    print(f"Connected to {len(bot.guilds)} servers and serving {len(bot.users)} users.")

# Commands
@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send("Pong!")

@bot.command()
async def status(ctx):
    """Check bot status (Admin Only)."""
    if not is_admin(ctx):
        await ctx.send("You don't have permission to use this command.")
        return
    server_count = len(bot.guilds)
    user_count = len(bot.users)
    await ctx.send(f"Bot is online!\nServers: {server_count}\nUsers: {user_count}")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member (requires kick permissions)."""
    if not ctx.author.guild_permissions.kick_members:
        await ctx.send("You don't have permission to kick members.")
        return
    await member.kick(reason=reason)
    await ctx.send(f"{member} has been kicked. Reason: {reason}")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member (requires ban permissions)."""
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("You don't have permission to ban members.")
        return
    await member.ban(reason=reason)
    await ctx.send(f"{member} has been banned. Reason: {reason}")

# Run the bot
bot.run(TOKEN)