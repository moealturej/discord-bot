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

load_dotenv()  # Load the environment file
token = os.getenv("DISCORD_TOKEN")

if not token:
    raise ValueError("DISCORD_TOKEN is not set in the environment or .env file.")

# Set up intents for the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Store bot uptime
start_time = datetime.datetime.now()

# Flask app for the dashboard
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Cache to hold the server count and update it periodically
server_count_cache = {'count': 0, 'last_updated': time.time()}

# Get bot's server count, status, and uptime for the web dashboard
def get_server_count():
    current_time = time.time()
    if current_time - server_count_cache['last_updated'] > 30:
        server_count_cache['count'] = len(bot.guilds)
        server_count_cache['last_updated'] = current_time
    return server_count_cache['count']

def get_bot_status():
    return "Online" if bot.is_ready() else "Offline"

def get_uptime():
    return str(datetime.datetime.now() - start_time)

@app.route('/')
def index():
    bot_status = get_bot_status()
    uptime = get_uptime()
    server_count = get_server_count()
    return render_template('index.html', bot_status=bot_status, uptime=uptime, server_count=server_count)

# Emit updates to frontend when status changes
@socketio.on('connect')
def on_connect():
    print('Client connected to SocketIO.')
    emit('status_update', {
        'bot_status': get_bot_status(),
        'uptime': get_uptime(),
        'server_count': get_server_count()
    })

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to run this command.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Please try again!")
    else:
        await ctx.send(f"An error occurred: {error}")

# Replace slash commands with .commands

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="uptime")
async def uptime(ctx):
    delta = datetime.datetime.now() - start_time
    await ctx.send(f"Uptime: {delta}")

@bot.command(name="purge")
async def purge(ctx, amount: int):
    """Delete a specific number of messages (Admin only)"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("You don't have the required permissions to purge messages.")
        return
    if amount <= 0:
        await ctx.send("You must specify a positive number of messages to delete.")
        return
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)

@bot.command(name="verify")
async def verify(ctx):
    """Send a verification code to the user"""
    verification_code = str(random.randint(1000, 9999))
    await ctx.send(f"Your verification code is: {verification_code}")
    await ctx.send("Please reply with the code to verify your identity.")
    
    def check(m):
        return m.content == verification_code and m.author == ctx.author

    try:
        msg = await bot.wait_for('message', check=check, timeout=60.0)
        await ctx.send("You have been verified!")
    except asyncio.TimeoutError:
        await ctx.send("Verification timed out.")

# Help Command with beautiful embed
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands for this bot:",
        color=discord.Color.purple()
    )

    embed.add_field(name=".ping", value="Responds with 'Pong!'", inline=False)
    embed.add_field(name=".uptime", value="Displays the bot's uptime.", inline=False)
    embed.add_field(name=".purge", value="Deletes a specified number of messages.", inline=False)
    embed.add_field(name=".verify", value="Sends a verification code to verify your identity.", inline=False)

    embed.set_footer(text="Use .help to get the list of commands anytime!")
    embed.set_thumbnail(url="https://i.postimg.cc/G2wZHDrz/standard11.gif")  # Your emblem here
    await ctx.send(embed=embed)

# To throttle updates to presence
@tasks.loop(minutes=5)  # Update presence every 5 minutes
async def update_presence():
    status = random.choice([ 
        f"🔥 Managing {len(bot.guilds)} legendary guilds",
        "🎮 Leveling up the gaming experience",
        f"💥 Empowering {len(bot.users)} epic players",
        "🚀 Unlocking new secrets and abilities"
    ])
    await bot.change_presence(activity=discord.Game(name=status))

# Set a cool avatar, banner, bot name, and description on ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    
    # Wait for a brief moment before attempting to change the avatar to avoid rate-limiting
    await asyncio.sleep(5)  # Adjust the delay if needed
    
    try:
        # Set avatar from image URL
        avatar_url = 'https://i.postimg.cc/G2wZHDrz/standard11.gif'  # Direct URL for the avatar
        async with bot.http._HTTPClient__session.get(avatar_url) as response:
            avatar_data = await response.read()
            await bot.user.edit(avatar=avatar_data)
        print("Avatar updated successfully.")
    except discord.errors.HTTPException as e:
        print(f"Error updating avatar: {e}")
    
    try:
        # Set the bot’s username
        await bot.user.edit(username="moealturej's bot")
    except discord.errors.HTTPException as e:
        print(f"Error updating username: {e}")
    
    # Set presence
    await bot.change_presence(activity=discord.Game(name=f"Use .help for commands"))
    
    # Emit updates to frontend after status change
    socketio.emit('status_update', {
        'bot_status': get_bot_status(),
        'uptime': get_uptime(),
        'server_count': get_server_count()
    })

    print(f"Bot is running with {len(bot.guilds)} moealturej services")
    update_presence.start()  # Start the presence update loop

# Function to keep the Flask app running alongside the bot
def run_flask():
    socketio.run(app, host='0.0.0.0', port=4000, use_reloader=False)

# Run both the bot and Flask app in different threads
def run_bot():
    token = os.getenv("DISCORD_TOKEN")
    try:
        bot.run(token)
    except discord.errors.HTTPException as e:
        if e.code == 429:
            print("Rate limit exceeded. Retrying after delay...")
            retry_after = e.retry_after  # Time to wait before retrying
            time.sleep(retry_after)
            run_bot()

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    run_bot()  # Run the Discord bot
