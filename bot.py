import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from threading import Thread
import time
import requests
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

# Store custom embeds
custom_embeds = {}

@app.route('/create_embed', methods=['POST'])
def create_embed():
    """Create a custom embed from the dashboard."""
    title = request.form.get('title')
    description = request.form.get('description')
    color = int(request.form.get('color', '0x3498db'), 16)  # Default color if not specified
    image_url = request.form.get('image_url')
    footer_text = request.form.get('footer_text')
    footer_icon = request.form.get('footer_icon')
    author_name = request.form.get('author_name')
    author_icon = request.form.get('author_icon')
    author_url = request.form.get('author_url')
    timestamp = bool(request.form.get('timestamp', False))

    # Create a new embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    # Optionally add an image or thumbnail
    if image_url:
        embed.set_image(url=image_url)
    
    # Add footer if provided
    if footer_text:
        embed.set_footer(text=footer_text, icon_url=footer_icon)

    # Add author if provided
    if author_name:
        embed.set_author(name=author_name, icon_url=author_icon, url=author_url)

    # Add timestamp if selected
    if timestamp:
        embed.timestamp = discord.utils.utcnow()

    # Generate unique ID for the embed
    embed_id = len(custom_embeds) + 1
    custom_embeds[embed_id] = embed

    return render_template('dashboard.html', embed_created=True, embed_id=embed_id)


@app.route('/get_embed/<int:embed_id>')
def get_embed(embed_id):
    """Fetch a custom embed."""
    embed = custom_embeds.get(embed_id)
    if not embed:
        return "Embed not found", 404

    # Convert the embed object to a dictionary to send as JSON
    embed_data = {
        'title': embed.title,
        'description': embed.description,
        'color': embed.color.value,
        'image_url': embed.image.url if embed.image else None,
        'footer_text': embed.footer.text if embed.footer else None,
        'footer_icon': embed.footer.icon_url if embed.footer else None,
        'author_name': embed.author.name if embed.author else None,
        'author_icon': embed.author.icon_url if embed.author else None,
        'author_url': embed.author.url if embed.author else None,
        'timestamp': embed.timestamp.isoformat() if embed.timestamp else None
    }

    return jsonify(embed_data)

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
    await ctx.author.send(f"🔒 Your verification code is: `{verification_code}`\nPlease reply with this code in this DM to verify.")

    def check(m):
        return m.content == verification_code and m.channel == ctx.author.dm_channel and m.author == ctx.author

    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.author.send("✅ You have been verified!")
    except asyncio.TimeoutError:
        await ctx.author.send("❌ Verification timed out. Please try again.")

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

@bot.command(name="send_embed")
async def send_embed(ctx, embed_id: int):
    """Send a fully customizable embed stored in the dashboard."""
    try:
        response = requests.get(f"http://localhost:4000/get_embed/{embed_id}")
        embed_data = response.json()
        
        embed = discord.Embed(
            title=embed_data['title'],
            description=embed_data['description'],
            color=embed_data['color']
        )

        # Add image, footer, author, and timestamp if provided
        if embed_data['image_url']:
            embed.set_image(url=embed_data['image_url'])
        
        if embed_data['footer_text']:
            embed.set_footer(text=embed_data['footer_text'], icon_url=embed_data['footer_icon'])
        
        if embed_data['author_name']:
            embed.set_author(
                name=embed_data['author_name'],
                icon_url=embed_data['author_icon'],
                url=embed_data['author_url']
            )
        
        if embed_data['timestamp']:
            embed.timestamp = discord.utils.parse_time(embed_data['timestamp'])
        
        await ctx.send(embed=embed)
    except requests.exceptions.RequestException as e:
        await ctx.send("❌ Failed to retrieve the embed.")
        print(f"Error retrieving embed: {e}")

# --- Flask App Thread ---
def run_flask():
    """Run Flask app."""
    socketio.run(app, host='0.0.0.0', port=4000)

# Run Flask and Discord bot
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
