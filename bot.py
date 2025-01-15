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

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in the environment or .env file.")

# Intents and bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Uptime tracking
start_time = datetime.datetime.now()

# Flask app setup
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, async_mode='eventlet')

# --- Flask Dashboard ---
def get_server_count():
    """Return the number of servers the bot is in."""
    return len(bot.guilds)

def get_bot_status():
    """Return the bot's online status."""
    return "🟢 Online" if bot.is_ready() else "🔴 Offline"

def get_uptime():
    """Return the bot's uptime."""
    return str(datetime.datetime.now() - start_time)

@app.route('/')
def index():
    """Render the dashboard."""
    return render_template('dashboard.html', 
                           bot_status=get_bot_status(), 
                           uptime=get_uptime(), 
                           server_count=get_server_count())

@socketio.on('connect')
def on_connect():
    """Emit bot status to connected clients."""
    emit('status_update', {
        'bot_status': get_bot_status(),
        'uptime': get_uptime(),
        'server_count': get_server_count()
    })

# --- Discord Bot Events ---
@bot.event
async def on_ready():
    """Triggered when the bot is ready."""
    print(f"✨ Logged in as {bot.user}! ✨")

    # Update avatar and presence
    try:
        avatar_url = 'https://i.postimg.cc/G2wZHDrz/standard11.gif'
        async with bot.http._HTTPClient__session.get(avatar_url) as response:
            avatar_data = await response.read()
            await bot.user.edit(avatar=avatar_data)
        print("🎨 Avatar updated successfully.")
    except discord.errors.HTTPException as e:
        print(f"Error updating avatar: {e}")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="Type .commands for help 💜"
    ))
    update_presence.start()

@tasks.loop(minutes=5)
async def update_presence():
    """Cycle through different statuses."""
    statuses = [
        "Managing your guilds! 🌌",
        "Keeping things stylish 💜",
        "Type .commands for fun & help!",
        f"Serving {len(bot.guilds)} servers!",
        "Let's make magic happen! ✨",
    ]
    await bot.change_presence(activity=discord.Game(name=random.choice(statuses)))

# --- Commands ---
@bot.command(name="ping")
async def ping(ctx):
    """Ping command."""
    await ctx.send("🏓 Pong! (Latency: {:.2f}ms)".format(bot.latency * 1000))

@bot.command(name="uptime")
async def uptime(ctx):
    """Show bot uptime."""
    delta = datetime.datetime.now() - start_time
    await ctx.send(f"⏱ Uptime: {delta}")

@bot.command(name="commands")
async def commands(ctx):
    """List all commands."""
    embed = discord.Embed(
        title="📜 Command List",
        description="Here are the commands you can use:",
        color=discord.Color.purple()
    )
    embed.add_field(name="🏓 .ping", value="Check the bot's response time.", inline=False)
    embed.add_field(name="⏱ .uptime", value="See how long the bot has been running.", inline=False)
    embed.add_field(name="🔒 .verify", value="Get a verification code in DMs.", inline=False)
    embed.add_field(name="🎟️ .create_ticket [reason]", value="Create a support ticket.", inline=False)
    embed.add_field(name="🎫 .close_ticket", value="Close the current ticket.", inline=False)
    embed.add_field(name="📌 .sticky [content]", value="Set a sticky message in the channel.", inline=False)
    embed.add_field(name="🔓 .unsticky", value="Remove the sticky message.", inline=False)
    embed.add_field(name="🖼 .send_embed [id]", value="Send a custom embed (via dashboard).", inline=False)
    embed.set_footer(text="Bot by moealturej")
    embed.set_thumbnail(url="https://i.postimg.cc/G2wZHDrz/standard11.gif")
    await ctx.send(embed=embed)

@bot.command(name="verify")
async def verify(ctx):
    """Send a verification code to the user."""
    verification_code = str(random.randint(1000, 9999))
    await ctx.author.send(f"🔒 Your verification code is `{verification_code}`.\nReply here to verify.")
    
    def check(m):
        return m.content == verification_code and m.channel == ctx.channel and m.author == ctx.author
    
    try:
        await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.author.send("✅ You are now verified!")
    except asyncio.TimeoutError:
        await ctx.author.send("❌ Verification timed out.")

# --- Ticket System ---
ticket_channels = {}

@bot.command(name="create_ticket")
async def create_ticket(ctx, *, reason="No reason provided"):
    """Create a ticket for support."""
    guild = ctx.guild
    if ctx.author.id in ticket_channels:
        await ctx.send("❌ You already have an open ticket.")
        return

    category = discord.utils.get(guild.categories, name="Tickets")
    if not category:
        category = await guild.create_category("Tickets")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    ticket_channel = await guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites, category=category)
    ticket_channels[ctx.author.id] = ticket_channel.id
    await ticket_channel.send(f"🎟️ Ticket created by {ctx.author.mention}\nReason: {reason}")

@bot.command(name="close_ticket")
async def close_ticket(ctx):
    """Close the ticket channel."""
    if ctx.channel.id not in ticket_channels.values():
        await ctx.send("❌ This is not a ticket channel.")
        return
    await ctx.channel.delete()
    del ticket_channels[ctx.author.id]

# --- Sticky Messages ---
sticky_messages = {}

@bot.command(name="sticky")
async def sticky(ctx, *, content):
    """Set a sticky message."""
    sticky_message = await ctx.send(content)
    sticky_messages[ctx.channel.id] = sticky_message

@bot.command(name="unsticky")
async def unsticky(ctx):
    """Remove sticky message."""
    if ctx.channel.id in sticky_messages:
        await sticky_messages[ctx.channel.id].delete()
        del sticky_messages[ctx.channel.id]

# --- Flask App Thread ---
def run_flask():
    """Run Flask app."""
    socketio.run(app, host='0.0.0.0', port=4000)

# Run Flask and Discord bot
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
