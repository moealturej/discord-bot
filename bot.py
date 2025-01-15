import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Thread
import time
import random
from dotenv import load_dotenv

load_dotenv()  # Load environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in the environment or .env file.")

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Variables for uptime and cache
start_time = datetime.datetime.now()
server_count_cache = {'count': 0, 'last_updated': time.time()}

# Flask app setup
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, async_mode='eventlet')


# --- Flask Dashboard ---
def get_server_count():
    """Return server count with caching."""
    current_time = time.time()
    if current_time - server_count_cache['last_updated'] > 30:
        server_count_cache['count'] = len(bot.guilds)
        server_count_cache['last_updated'] = current_time
    return server_count_cache['count']


def get_bot_status():
    """Return bot's status."""
    return "Online" if bot.is_ready() else "Offline"


def get_uptime():
    """Return bot's uptime."""
    return str(datetime.datetime.now() - start_time)


@app.route('/')
def index():
    """Render the dashboard."""
    bot_status = get_bot_status()
    uptime = get_uptime()
    server_count = get_server_count()
    return render_template('dashboard.html', bot_status=bot_status, uptime=uptime, server_count=server_count)


@socketio.on('connect')
def on_connect():
    """Emit bot status to connected clients."""
    emit('status_update', {
        'bot_status': get_bot_status(),
        'uptime': get_uptime(),
        'server_count': get_server_count()
    })


# --- Discord Bot Commands ---
@bot.event
async def on_ready():
    """Bot is ready event."""
    print(f"Logged in as {bot.user}!")

    # Update bot's avatar and presence
    try:
        avatar_url = 'https://i.postimg.cc/G2wZHDrz/standard11.gif'
        async with bot.http._HTTPClient__session.get(avatar_url) as response:
            avatar_data = await response.read()
            await bot.user.edit(avatar=avatar_data)
        print("Avatar updated successfully.")
    except discord.errors.HTTPException as e:
        print(f"Error updating avatar: {e}")

    await bot.change_presence(activity=discord.Game(name="Use .help for commands"))
    print(f"Bot is serving {len(bot.guilds)} guilds!")
    update_presence.start()  # Start the presence update task


# Verification Command
@bot.command(name="verify")
async def verify(ctx):
    """Send a verification code to the user."""
    verification_code = str(random.randint(1000, 9999))
    await ctx.author.send(f"🔒 Your verification code is: `{verification_code}`\nPlease reply with this code in this DM to verify.")
    
    def check(m):
        return m.content == verification_code and m.channel == ctx.channel and m.author == ctx.author
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.author.send("✅ You have been verified!")
    except asyncio.TimeoutError:
        await ctx.author.send("❌ Verification timed out. Please try again.")

# Ticket System
ticket_channels = {}

@bot.command(name="create_ticket")
async def create_ticket(ctx, *, reason="No reason provided"):
    """Create a ticket for support."""
    guild = ctx.guild
    if ctx.author.id in ticket_channels:
        await ctx.send("❌ You already have an open ticket.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    category = discord.utils.get(guild.categories, name="Tickets")
    if not category:
        category = await guild.create_category("Tickets")

    ticket_channel = await guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites, category=category)
    ticket_channels[ctx.author.id] = ticket_channel.id

    await ticket_channel.send(f"🎟️ Ticket created by {ctx.author.mention}\nReason: {reason}")
    await ctx.send(f"✅ Ticket created: {ticket_channel.mention}")

@bot.command(name="close_ticket")
async def close_ticket(ctx):
    """Close the current ticket."""
    if ctx.channel.id not in ticket_channels.values():
        await ctx.send("❌ This is not a ticket channel.")
        return

    user_id = list(ticket_channels.keys())[list(ticket_channels.values()).index(ctx.channel.id)]
    await ctx.channel.delete()
    del ticket_channels[user_id]
    await ctx.send(f"✅ Ticket for {ctx.author.mention} has been closed.", delete_after=5)

# Sticky Messages
sticky_messages = {}

@bot.event
async def on_message(message):
    if message.channel.id in sticky_messages and not message.author.bot:
        sticky_message = sticky_messages[message.channel.id]
        await sticky_message.delete()
        sticky_messages[message.channel.id] = await message.channel.send(sticky_message.content)
    await bot.process_commands(message)

@bot.command(name="sticky")
async def sticky(ctx, *, content):
    """Set a sticky message."""
    if ctx.channel.id in sticky_messages:
        await ctx.send("❌ This channel already has a sticky message.")
        return

    sticky_message = await ctx.send(content)
    sticky_messages[ctx.channel.id] = sticky_message
    await ctx.send("✅ Sticky message set.")

@bot.command(name="unsticky")
async def unsticky(ctx):
    """Remove the sticky message from the channel."""
    if ctx.channel.id not in sticky_messages:
        await ctx.send("❌ No sticky message in this channel.")
        return

    await sticky_messages[ctx.channel.id].delete()
    del sticky_messages[ctx.channel.id]
    await ctx.send("✅ Sticky message removed.")

# Custom Embed System
custom_embeds = {}

@bot.command(name="create_embed")
async def create_embed(ctx, title: str, description: str, color: str = '#3498db', footer: str = '', thumbnail_url: str = ''):
    """Create and store a custom embed."""
    try:
        color = int(color.lstrip('#'), 16)
    except ValueError:
        await ctx.send("❌ Invalid color format. Use a valid hex color code.")
        return

    embed = discord.Embed(title=title, description=description, color=color)
    if footer:
        embed.set_footer(text=footer)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    embed_id = len(custom_embeds) + 1  # Generate a new ID for the embed
    custom_embeds[embed_id] = embed.to_dict()
    await ctx.send(f"✅ Embed created with ID: {embed_id}")


@bot.command(name="send_embed")
async def send_embed(ctx, embed_id: int):
    """Send a custom embed stored by the dashboard."""
    if embed_id not in custom_embeds:
        await ctx.send("❌ No embed found with that ID.")
        return

    embed_data = custom_embeds[embed_id]
    embed = discord.Embed.from_dict(embed_data)
    await ctx.send(embed=embed)


@tasks.loop(minutes=5)
async def update_presence():
    """Update bot's presence every 5 minutes."""
    status = random.choice([
        f"Use .commands to explore features!",
        "Type .commands for help and tips!",
        "Check out .commands for all commands!",
        f"Managing {len(bot.guilds)} guilds—use .commands!",
        f"Helping {len(bot.users)} users—type .commands!",
        "Looking for help? Try .commands!",
        "Discover new features with .commands!",
    ])
    await bot.change_presence(activity=discord.Game(name=status))


# --- Flask App Thread ---
def run_flask():
    socketio.run(app, host='0.0.0.0', port=4000, use_reloader=False)


# --- Run Bot ---
if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)
