from flask import Flask, jsonify, request, render_template
from threading import Thread
from discord.ext.commands import Bot
import os

app = Flask(__name__)

# Placeholder for the bot instance
bot_instance = None


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/bot_status")
def bot_status():
    if bot_instance and bot_instance.is_ready():
        return jsonify({
            "online": True,
            "server_count": len(bot_instance.guilds),
            "user_count": sum(guild.member_count for guild in bot_instance.guilds),
            "commands": [cmd.name for cmd in bot_instance.commands]
        })
    else:
        return jsonify({
            "online": False,
            "server_count": 0,
            "user_count": 0,
            "commands": []
        })


@app.route("/bot_action", methods=["POST"])
def bot_action():
    data = request.json
    if data["action"] == "start":
        start_bot()
        return jsonify({"status": "Bot started"})
    elif data["action"] == "stop":
        stop_bot()
        return jsonify({"status": "Bot stopped"})
    else:
        return jsonify({"status": "Invalid action"})


def start_bot():
    global bot_instance
    if bot_instance is None:
        from bot import bot
        bot_instance = bot
        thread = Thread(target=bot.run, args=(os.getenv("DISCORD_BOT_TOKEN"),))
        thread.start()


def stop_bot():
    global bot_instance
    if bot_instance:
        bot_instance.close()
        bot_instance = None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
