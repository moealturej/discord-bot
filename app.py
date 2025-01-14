from flask import Flask, render_template, jsonify, request
import threading
import os
import time
import subprocess

# Simulated live bot stats
bot_status = {"online": False, "server_count": 0, "user_count": 0, "commands": []}

# Flask app setup
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/bot_status")
def get_bot_status():
    """Provide live bot statistics."""
    return jsonify(bot_status)

@app.route("/bot_action", methods=["POST"])
def bot_action():
    """Control the bot (start/stop)."""
    action = request.json.get("action")
    if action == "start":
        if not bot_status["online"]:
            threading.Thread(target=start_bot, daemon=True).start()
            return jsonify({"status": "Bot starting..."})
        return jsonify({"status": "Bot already running."})
    elif action == "stop":
        bot_status["online"] = False
        return jsonify({"status": "Bot stopped."})
    return jsonify({"status": "Invalid action."}), 400

@app.route("/add_command", methods=["POST"])
def add_command():
    """Add a custom command to the bot."""
    command = request.json.get("command")
    if command:
        bot_status["commands"].append(command)
        return jsonify({"status": "Command added."})
    return jsonify({"status": "Invalid command."}), 400

def start_bot():
    """Simulate starting the bot process."""
    bot_status["online"] = True
    bot_status["server_count"] = 5
    bot_status["user_count"] = 100
    while bot_status["online"]:
        # Simulate real-time updates
        bot_status["server_count"] += 1  # Increment for demo purposes
        bot_status["user_count"] += 10  # Increment for demo purposes
        time.sleep(10)

# Run Flask app
if __name__ == "__main__":
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)