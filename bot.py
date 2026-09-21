# ============ HIDE TOKEN FROM LOGS ============
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

import os
import random
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set!")

# ============ WORD LIST ============
WORDS = [
    "python", "telegram", "computer", "internet", "keyboard",
    "monitor", "program", "developer", "database", "network",
    "software", "hardware", "website", "browser", "server",
    "algorithm", "variable", "function", "security", "password",
    "elephant", "giraffe", "mountain", "ocean", "rainbow",
    "butterfly", "chocolate", "adventure", "treasure", "mystery"
]

# Store game state per user
games = {}
scores = {}

# ============ HELPERS ============
def scramble_word(word):
    letters = list(word)
    random.shuffle(letters)
    scrambled = ''.join(letters)
    while scrambled == word and len(word) > 1:
        random.shuffle(letters)
        scrambled = ''.join(letters)
    return scrambled

def get_hint(word, revealed_letters):
    hint = ""
    for i, letter in enumerate(word):
        if i in revealed_letters:
            hint += letter + " "
        else:
            hint += "_ "
    return hint.strip()

# ============ FLASK - KEEPS HOST ALIVE ============
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Word Scramble Bot is running!", 200

# ============ COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = (
        f"Hi {user.first_name}! Welcome to <b>Word Scramble Game!</b>\n\n"
        "How to play:\n"
        "1. I give you a scrambled word\n"
        "2. You guess the correct word\n"
        "3. Type your answer and send it!\n\n"
        "<b>Commands:</b>\n"
        "/play - Start a new game\n"
        "/hint - Get a hint\n"
        "/skip - Skip current word\n"
        "/score - See your score\n"
        "/help - Get help\n\n"
        "Ready to play? Send /play to start!"
    )
    await update.message.reply_text(welcome_message, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>How to play Word Scramble:</b>\n\n"
        "1. Send /play to get a scrambled word\n"
        "2. Type your answer and send it\n"
        "3. Send /hint to reveal a letter\n"
        "4. Send /skip to skip the word\n"
        "5. Send /score to see your points\n\n"
        "<b>Scoring:</b>\n"
        "Correct answer: +10 points\n"
        "Using hint: -1 point\n"
        "Skipping: -2 points\n\n"
        "Send /play to start playing!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = random.choice(WORDS)
    scrambled = scramble_word(word)

    games[user_id] = {
        'word': word,
        'scrambled': scrambled,
        'attempts': 0,
        'revealed': set(),
        'hints_used': 0
    }

    if user_id not in scores:
        scores[user_id] = 0

    message = (
        "<b>Word Scramble</b>\n\n"
        "Unscramble this word:\n\n"
        f"<code>{scrambled.upper()}</code>\n\n"
        f"Length: {len(word)} letters\n\n"
        "Type your answer below!\n"
        "Need help? Send /hint"
    )
    await update.message.reply_text(message, parse_mode='HTML')

async def hint_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in games:
        await update.message.reply_text(
            "No active game!\n\nSend /play to start a new game."
        )
        return

    game = games[user_id]
    word = game['word']
    revealed = game['revealed']
    unrevealed = [i for i in range(len(word)) if i not in revealed]

    if not unrevealed:
        await update.message.reply_text(
            f"All letters are already revealed!\n\n"
            f"The word is: <code>{word.upper()}</code>\n\n"
            "Type it to complete the game!",
            parse_mode='HTML'
        )
        return

    position = random.choice(unrevealed)
    revealed.add(position)
    game['hints_used'] += 1

    if user_id not in scores:
        scores[user_id] = 0
    scores[user_id] -= 1

    hint_display = get_hint(word, revealed)

    message = (
        f"<b>Hint Revealed!</b>\n\n"
        f"<code>{hint_display}</code>\n\n"
        f"Hints used: {game['hints_used']} (-1 point)\n\n"
        "Keep guessing!"
    )
    await update.message.reply_text(message, parse_mode='HTML')

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in games:
        await update.message.reply_text(
            "No active game!\n\nSend /play to start a new game."
        )
        return

    game = games[user_id]
    word = game['word']

    if user_id not in scores:
        scores[user_id] = 0
    scores[user_id] -= 2

    del games[user_id]

    message = (
        f"<b>Word Skipped!</b>\n\n"
        f"The word was: <code>{word.upper()}</code>\n\n"
        "Skipping cost: -2 points\n\n"
        "Send /play to try another word!"
    )
    await update.message.reply_text(message, parse_mode='HTML')

async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = scores.get(user_id, 0)

    if score >= 100:
        rank = "Word Master"
    elif score >= 50:
        rank = "Expert"
    elif score >= 25:
        rank = "Advanced"
    elif score >= 10:
        rank = "Intermediate"
    else:
        rank = "Beginner"

    message = (
        "<b>Your Score</b>\n\n"
        f"Points: {score}\n"
        f"Rank: {rank}\n\n"
        "Keep playing to earn more points!\n"
        "Send /play to continue!"
    )
    await update.message.reply_text(message, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()

    if user_id not in games:
        await update.message.reply_text(
            "No active game!\n\nSend /play to start a new game."
        )
        return

    game = games[user_id]
    word = game['word']
    game['attempts'] += 1

    if guess == word:
        base_points = 10
        hint_penalty = game['hints_used']
        points_earned = max(1, base_points - hint_penalty)

        if user_id not in scores:
            scores[user_id] = 0
        scores[user_id] += points_earned
        total_score = scores[user_id]

        message = (
            "<b>CORRECT!</b>\n\n"
            f"The word was: <code>{word.upper()}</code>\n\n"
            f"Attempts: {game['attempts']}\n"
            f"Hints used: {game['hints_used']}\n"
            f"Points earned: +{points_earned}\n"
            f"Total score: {total_score}\n\n"
            "Send /play for another word!"
        )
        del games[user_id]
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        message = (
            "<b>Wrong!</b> Try again.\n\n"
            f"<code>{game['scrambled'].upper()}</code>\n\n"
            f"Length: {len(word)} letters\n"
            f"Attempts: {game['attempts']}\n\n"
            "Send /hint for a hint\n"
            "Send /skip to skip"
        )
        await update.message.reply_text(message, parse_mode='HTML')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ============ BOT STARTUP ============
async def run_bot_async():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("play", play_command))
    app.add_handler(CommandHandler("hint", hint_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    logger.info("Word Scramble Bot is polling and ready!")
    while True:
        await asyncio.sleep(1)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
