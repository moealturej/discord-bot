import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
from flask import Flask, render_template
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


@bot.command(name="ping")
async def ping(ctx):
    """Respond with 'Pong!'."""
    await ctx.send("🏓 Pong!")


@bot.command(name="uptime")
async def uptime(ctx):
    """Send the bot's uptime."""
    delta = datetime.datetime.now() - start_time
    await ctx.send(f"⏱ Uptime: {delta}")


@bot.command(name="purge")
async def purge(ctx, amount: int):
    """Delete messages (Admin only)."""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You don't have permission to use this command.")
        return
    if amount <= 0:
        await ctx.send("❌ Please specify a positive number of messages.")
        return
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"✅ Deleted {len(deleted)} messages.", delete_after=5)


@bot.command(name="help")
async def help_command(ctx):
    """Send a help message."""
    embed = discord.Embed(
        title="📜 Command List",
        description="Here are the commands you can use:",
        color=discord.Color.blue()
    )
    embed.add_field(name=".ping", value="Responds with 'Pong!'", inline=False)
    embed.add_field(name=".uptime", value="Shows the bot's uptime.", inline=False)
    embed.add_field(name=".purge [amount]", value="Deletes messages (Admin only).", inline=False)
    embed.add_field(name=".help", value="Shows this help message.", inline=False)
    embed.set_footer(text="Bot by moealturej")
    embed.set_thumbnail(url="https://i.postimg.cc/G2wZHDrz/standard11.gif")
    await ctx.send(embed=embed)


@tasks.loop(minutes=5)
async def update_presence():
    """Update bot's presence every 5 minutes."""
    status = random.choice([
        f"Serving {len(bot.guilds)} guilds",
        "Helping users level up",
        "Bringing communities together"
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
