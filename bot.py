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

load_dotenv()

# Set up intents for the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store bot uptime
start_time = datetime.datetime.now()

# Flask app for the dashboard
app = Flask(__name__)
socketio = SocketIO(app)

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

# Basic commands for the Discord bot
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def uptime(ctx):
    delta = datetime.datetime.now() - start_time
    await ctx.send(f"Uptime: {delta}")

# To throttle updates to presence
@tasks.loop(minutes=5)  # Update presence every 5 minutes
async def update_presence():
    status = random.choice([
        f"Serving {len(bot.guilds)} servers",
        "🎮 Playing games",
        "Helping {len(bot.users)} users",
        "Learning new tricks"
    ])
    await bot.change_presence(activity=discord.Game(name=status))

# Set a cool avatar, banner, bot name, and description on ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    
    # Set avatar from image URL
    avatar_url = 'https://i.postimg.cc/G2wZHDrz/standard11.gif'  # Direct URL for the avatar
    async with bot.http._HTTPClient__session.get(avatar_url) as response:
        avatar_data = await response.read()
        await bot.user.edit(avatar=avatar_data)
    
    # Set the bot’s username
    await bot.user.edit(username="moealturej's bot")
    
    # Set presence
    await bot.change_presence(activity=discord.Game(name=f"Serving {len(bot.guilds)} servers"))
    
    # Emit updates to the frontend after status change
    socketio.emit('status_update', {
        'bot_status': get_bot_status(),
        'uptime': get_uptime(),
        'server_count': get_server_count()
    })

    print(f"Bot is running with {len(bot.guilds)} moealturej services")
    update_presence.start()  # Start the presence update loop

@bot.event
async def on_disconnect():
    print(f"Bot disconnected")

# Function to keep the Flask app running alongside the bot
def run_flask():
    socketio.run(app, host='0.0.0.0', port=4000)

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
