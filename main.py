from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from collections import defaultdict
from datetime import datetime, timedelta
import threading
import time
import pytz
import json
import os
from keep_alive import keep_alive

TOKEN = "7059991765:AAH-vq6A4gU4Bw7tJmrjqug2Un5Nb7j1IzA"
DATA_PATH = "bot_data.json"

user_points = defaultdict(int)
user_claimed_gm = {}
user_invite_count = defaultdict(int)
tasks = defaultdict(list)
chat_state = defaultdict(lambda: None)
user_display_names = {}
user_joined_from = {}

def save_data():
    with open(DATA_PATH, "w") as f:
        json.dump({
            "user_points": dict(user_points),
            "user_claimed_gm": {k: v.isoformat() for k, v in user_claimed_gm.items()},
            "user_joined_from": user_joined_from
        }, f)

def load_data():
    if not os.path.exists(DATA_PATH):
        return
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
        user_points.update({int(k): int(v) for k, v in data.get("user_points", {}).items()})
        user_claimed_gm.update({int(k): datetime.fromisoformat(v) for k, v in data.get("user_claimed_gm", {}).items()})
        user_joined_from.update({int(k): int(v) for k, v in data.get("user_joined_from", {}).items()})

load_data()

instructions = "Welcome to the bot! Use /gm, /giveaway, /leaderboard, /invite and more."

def add_points(user_id, points):
    user_points[user_id] += points
    save_data()

def get_points(user_id):
    return user_points.get(user_id, 0)

def get_leaderboard(user_id):
    sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
    leaderboard = "🏆 Giveaway Leaderboard:
"
    for i in range(5):
        if i < len(sorted_users):
            uid, pts = sorted_users[i]
            name = user_display_names.get(uid, f"User {uid}")
            leaderboard += f"{i+1}. {name} ({pts} points)
"
        else:
            leaderboard += f"{i+1}.
"
    rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), "N/A")
    leaderboard += f"
🔹 Your Rank: {rank} | Your Points: {get_points(user_id)}"
    return leaderboard

def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user = update.message.from_user
    display_name = user.username or f"{user.first_name} {user.last_name or ''}".strip()
    user_display_names[user_id] = display_name

    args = context.args
    if args and args[0].isdigit():
        inviter_id = int(args[0])
        if user_id != inviter_id and user_id not in user_joined_from:
            user_joined_from[user_id] = inviter_id
            user_invite_count[inviter_id] += 1
            add_points(inviter_id, 20)

    if user_id not in user_points:
        add_points(user_id, 10)
        context.bot.send_message(chat_id=user_id, text=f"👋 Welcome!
You've earned 10 giveaway points for joining!

{instructions}")
    else:
        context.bot.send_message(chat_id=user_id, text=f"👋 Welcome back!
{instructions}")

def invite(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    context.bot.send_message(chat_id=uid, text=f"🔗 Your Invite Link: https://t.me/ClientOS_Bot?start={uid}")

def checkinvites(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    joined = user_invite_count.get(uid, 0)
    context.bot.send_message(chat_id=uid, text=f"👥 People who joined through you: {joined}
💰 Points earned from invites: {joined * 20}")

def giveaway(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    context.bot.send_message(chat_id=uid, text=f"🎟️ You currently have {get_points(uid)} giveaway points.")

def leaderboard(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.message.chat_id, text=get_leaderboard(update.message.chat_id))

def gm(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    now = datetime.utcnow()
    if uid not in user_claimed_gm or now - user_claimed_gm[uid] >= timedelta(hours=24):
        user_claimed_gm[uid] = now
        add_points(uid, 1)
        context.bot.send_message(chat_id=uid, text=f"🌅 GM! You earned 1 giveaway point. Total: {get_points(uid)} points.")
    else:
        remaining = timedelta(hours=24) - (now - user_claimed_gm[uid])
        context.bot.send_message(chat_id=uid, text=f"⚠️ You already claimed your GM point today. Try again in {str(remaining).split('.')[0]}.")

def daily_scheduler(bot):
    message = "📢 Daily Reminder:
Type /gm to get your point.
Use /invite to earn more.
Check /leaderboard to see your rank."
    while True:
        now = datetime.now(pytz.timezone("Europe/London"))
        if now.hour == 12 and now.minute == 0:
            for user_id in user_points.keys():
                bot.send_message(chat_id=user_id, text=message)
            time.sleep(60)
        time.sleep(1)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_args=True))
    dp.add_handler(CommandHandler("giveaway", giveaway))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(CommandHandler("invite", invite))
    dp.add_handler(CommandHandler("checkinvites", checkinvites))
    dp.add_handler(CommandHandler("gm", gm))

    threading.Thread(target=daily_scheduler, args=(updater.bot,), daemon=True).start()
    keep_alive()
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
