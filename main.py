from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from collections import defaultdict
from datetime import datetime, timedelta
import threading
import time
import pytz
import os
import json

# Token and data path for Railway
TOKEN = "7059991765:AAH-vq6A4gU4Bw7tJmrjqug2Un5Nb7j1IzA"
DATA_PATH = "bot_data.json"

# Initialize variables
user_points = defaultdict(int)
user_claimed_gm = {}
user_invite_count = defaultdict(int)
tasks = defaultdict(list)
chat_state = defaultdict(lambda: None)
user_display_names = {}
user_joined_from = {}

# Categories for Outreach & Follow-ups
outreach_categories = {
    "1": "Problem Solver",
    "2": "Saw You Mention Approach",
    "3": "Competitor Advantage",
    "4": "Mini Audit",
    "5": "Dream Scenario",
    "6": "I Already Did The Work",
    "7": "Blunt Callout",
    "8": "Reverse Testimonial",
    "9": "Straight to the Offer",
    "10": "Referral Request"
}

followup_categories = {
    "1": "Did You See This?",
    "2": "Value Drop",
    "3": "I Noticed Something",
    "4": "Social Proof",
    "5": "Straight Shooter",
    "6": "Curiosity Hook",
    "7": "Last Chance",
    "8": "Personalized Pattern Interrupt",
    "9": "Reposition & Refresh",
    "10": "Brutal Honesty"
}

# Templates
outreach_templates = {
    "1": "Subject: Quick fix for [specific problem]...",
    "2": "Subject: About your [post/tweet on X]...",
    # More outreach templates here...
}

followup_templates = {
    "1": "SUBJECT: Did you see this?...",
    "2": "SUBJECT: Saw this and thought of you...",
    # More follow-up templates here...
}

# Instructions
instructions = """🎟️ How to Earn Giveaway Points:
- 10 points for joining
- 20 points if someone you invite joins
- 1 point for saying "GM" once per day

🏆 Commands to Check Your Progress:
/giveaway → See your current points
/leaderboard → View the top 5 users + your ranking
/invite → Get your invite link
/checkinvites → See how many people joined & total points earned

📩 Get Outreach Templates:
/outreach → Choose a category
/followups → Choose a category

🔍 Stay Updated:
/updates → Check for software updates
/demo → See available demos (coming soon!)

📋 Task Management:
/tasks → View your tasks
/addtask → Add a new task
/completetask → Complete a task by number

📬 Content:
/lastemail → View the latest newsletter
/latesttweet → View the latest tweet

🕛 Daily Broadcast:
A daily message will be shared here every day at 12PM UK time.
"""

# Functions to save and load data
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

# Functions for Commands
def add_points(user_id, points):
    user_points[user_id] += points
    save_data()

def get_points(user_id):
    return user_points.get(user_id, 0)

def get_leaderboard(user_id):
    sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)
    leaderboard = "🏆 Giveaway Leaderboard:\n"
    for i in range(5):
        if i < len(sorted_users):
            uid, pts = sorted_users[i]
            name = user_display_names.get(uid, f"User {uid}")
            leaderboard += f"{i+1}. {name} ({pts} points)\n"
        else:
            leaderboard += f"{i+1}.\n"
    rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), "N/A")
    leaderboard += f"\n🔹 Your Rank: {rank} | Your Points: {get_points(user_id)}"
    return leaderboard

def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user = update.message.from_user
    display_name = user.username or f"{user.first_name} {user.last_name or ''}".strip()
    user_display_names[user_id] = display_name

    if user_id not in user_points:
        add_points(user_id, 10)
        context.bot.send_message(chat_id=user_id, text=f"👋 Welcome to ClientOS Insider!\nYou've earned 10 giveaway points for joining!\n\n{instructions}")
    else:
        context.bot.send_message(chat_id=user_id, text=f"👋 Welcome back to ClientOS Insider!\n{instructions}")

def outreach(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    chat_state[uid] = "outreach"
    text = "📩 Choose an Outreach Template Category:\n" + "\n".join([f"{k}. {v}" for k, v in outreach_categories.items()]) + "\n\nReply with the number."
    context.bot.send_message(chat_id=uid, text=text)

def followups(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    chat_state[uid] = "followups"
    text = "📩 Choose a Follow-Up Template Category:\n" + "\n".join([f"{k}. {v}" for k, v in followup_categories.items()]) + "\n\nReply with the number."
    context.bot.send_message(chat_id=uid, text=text)

def handle_number(update: Update, context: CallbackContext):
    uid = update.message.chat_id
    cmd = update.message.text.strip()
    if chat_state[uid] == "outreach" and cmd in outreach_templates:
        context.bot.send_message(chat_id=uid, text=outreach_templates[cmd])
        chat_state[uid] = None
    elif chat_state[uid] == "followups" and cmd in followup_templates:
        context.bot.send_message(chat_id=uid, text=followup_templates[cmd])
        chat_state[uid] = None

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
    message = "📢 Daily Reminder:\n- Type /gm to claim your point.\n- Use /invite to earn more.\n- Check /leaderboard to see your rank."
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

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("giveaway", giveaway))
    dp.add_handler(CommandHandler("leaderboard", leaderboard))
    dp.add_handler(CommandHandler("invite", invite))
    dp.add_handler(CommandHandler("checkinvites", checkinvites))
    dp.add_handler(CommandHandler("updates", updates))
    dp.add_handler(CommandHandler("demo", demo))
    dp.add_handler(CommandHandler("outreach", outreach))
    dp.add_handler(CommandHandler("followups", followups))
    dp.add_handler(CommandHandler("tasks", tasks_cmd))
    dp.add_handler(CommandHandler("addtask", addtask))
    dp.add_handler(CommandHandler("completetask", completetask))
    dp.add_handler(CommandHandler("gm", gm))
    dp.add_handler(CommandHandler("lastemail", lastemail))
    dp.add_handler(CommandHandler("latesttweet", latesttweet))
    dp.add_handler(MessageHandler(Filters.regex("^[0-9]+$"), handle_number))

    threading.Thread(target=daily_scheduler, args=(updater.bot,), daemon=True).start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
