import os
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Word list for the game
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

def scramble_word(word):
    """Scramble the letters of a word"""
    letters = list(word)
    random.shuffle(letters)
    scrambled = ''.join(letters)
    # Make sure it's different from original
    while scrambled == word and len(word) > 1:
        random.shuffle(letters)
        scrambled = ''.join(letters)
    return scrambled

def get_hint(word, revealed_letters):
    """Get a hint showing some letters"""
    hint = ""
    for i, letter in enumerate(word):
        if i in revealed_letters:
            hint += letter + " "
        else:
            hint += "_ "
    return hint.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    user = update.effective_user
    
    welcome_message = f"""
🎮 *Welcome to Word Scramble Game!*

Hi {user.first_name}! Let's play a fun word game!

🎯 *How to play:*
1. I'll give you a scrambled word
2. You need to guess the correct word
3. Type your answer and send it!

📝 *Commands:*
/start - Show this message
/play - Start a new game
/hint - Get a hint (reveals a letter)
/skip - Skip current word
/score - See your score
/help - Get help

*Ready to play? Send /play to start!* 🚀
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
🆘 *How to play Word Scramble:*

1️⃣ *Start a game*
Send /play to get a scrambled word

2️⃣ *Guess the word*
Type your answer and send it

3️⃣ *Use hints*
Send /hint to reveal a letter (costs 1 point)

4️⃣ *Skip*
Send /skip to skip the current word

5️⃣ *Check score*
Send /score to see your points

🎯 *Scoring:*
• Correct answer: +10 points
• Using hint: -1 point
• Skipping: -2 points

💡 *Tips:*
• Words are common English words
• All words are lowercase
• Look for patterns in the letters

*Send /play to start playing!* 🎮
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new game"""
    user_id = update.effective_user.id
    
    # Pick a random word
    word = random.choice(WORDS)
    scrambled = scramble_word(word)
    
    # Store game state
    games[user_id] = {
        'word': word,
        'scrambled': scrambled,
        'attempts': 0,
        'revealed': set(),
        'hints_used': 0
    }
    
    # Initialize score if not exists
    if 'scores' not in context.bot_data:
        context.bot_data['scores'] = {}
    if user_id not in context.bot_data['scores']:
        context.bot_data['scores'][user_id] = 0
    
    # Send scrambled word
    message = f"""
🎮 *Word Scramble*

Unscramble this word:

🔤 `{scrambled.upper()}`

📏 *Length:* {len(word)} letters

Type your answer below! 👇

💡 Need help? Send /hint
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def hint_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give a hint"""
    user_id = update.effective_user.id
    
    if user_id not in games:
        await update.message.reply_text(
            "❌ *No active game!*\n\nSend /play to start a new game.",
            parse_mode='Markdown'
        )
        return
    
    game = games[user_id]
    word = game['word']
    revealed = game['revealed']
    
    # Find unrevealed positions
    unrevealed = [i for i in range(len(word)) if i not in revealed]
    
    if not unrevealed:
        await update.message.reply_text(
            "🎯 *All letters are already revealed!*\n\n"
            f"The word is: `{word.upper()}`\n\n"
            "Type it to complete the game!",
            parse_mode='Markdown'
        )
        return
    
    # Reveal a random letter
    position = random.choice(unrevealed)
    revealed.add(position)
    game['hints_used'] += 1
    
    # Deduct point
    context.bot_data['scores'][user_id] -= 1
    
    hint_display = get_hint(word, revealed)
    
    message = f"""
💡 *Hint Revealed!*

`{hint_display}`

📊 *Hint used:* {game['hints_used']} (-1 point)

Keep guessing! 👇
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip current word"""
    user_id = update.effective_user.id
    
    if user_id not in games:
        await update.message.reply_text(
            "❌ *No active game!*\n\nSend /play to start a new game.",
            parse_mode='Markdown'
        )
        return
    
    game = games[user_id]
    word = game['word']
    
    # Deduct points
    context.bot_data['scores'][user_id] -= 2
    
    # Remove game
    del games[user_id]
    
    message = f"""
⏭️ *Word Skipped!*

The word was: `{word.upper()}`

📊 *Skipping cost:* -2 points

Send /play to try another word!
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show player's score"""
    user_id = update.effective_user.id
    
    if 'scores' not in context.bot_data:
        context.bot_data['scores'] = {}
    
    score = context.bot_data['scores'].get(user_id, 0)
    
    # Get rank
    if score >= 100:
        rank = "🏆 Word Master"
    elif score >= 50:
        rank = "🥇 Expert"
    elif score >= 25:
        rank = "🥈 Advanced"
    elif score >= 10:
        rank = "🥉 Intermediate"
    else:
        rank = "🌱 Beginner"
    
    message = f"""
📊 *Your Score*

⭐ *Points:* `{score}`
🎖️ *Rank:* {rank}

Keep playing to earn more points!

Send /play to continue! 🎮
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle player's guess"""
    user_id = update.effective_user.id
    guess = update.message.text.strip().lower()
    
    if user_id not in games:
        await update.message.reply_text(
            "❌ *No active game!*\n\nSend /play to start a new game.",
            parse_mode='Markdown'
        )
        return
    
    game = games[user_id]
    word = game['word']
    game['attempts'] += 1
    
    if guess == word:
        # Correct answer!
        base_points = 10
        hint_penalty = game['hints_used']
        points_earned = max(1, base_points - hint_penalty)
        
        # Update score
        if 'scores' not in context.bot_data:
            context.bot_data['scores'] = {}
        context.bot_data['scores'][user_id] = context.bot_data['scores'].get(user_id, 0) + points_earned
        
        total_score = context.bot_data['scores'][user_id]
        
        message = f"""
🎉 *CORRECT!*

✅ The word was: `{word.upper()}`

📊 *Results:*
• Attempts: {game['attempts']}
• Hints used: {game['hints_used']}
• Points earned: +{points_earned}
• Total score: {total_score}

Send /play for another word! 🎮
"""
        
        # Remove game
        del games[user_id]
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    else:
        # Wrong answer
        remaining_letters = len(word) - len(game['revealed'])
        
        message = f"""
❌ *Wrong!* Try again.

🔤 `{game['scrambled'].upper()}`

📏 *Length:* {len(word)} letters
🎯 *Attempts:* {game['attempts']}

💡 Send /hint for a hint
⏭️ Send /skip to skip
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "play":
        # Simulate /play command
        user_id = query.from_user.id
        
        word = random.choice(WORDS)
        scrambled = scramble_word(word)
        
        games[user_id] = {
            'word': word,
            'scrambled': scrambled,
            'attempts': 0,
            'revealed': set(),
            'hints_used': 0
        }
        
        if 'scores' not in context.bot_data:
            context.bot_data['scores'] = {}
        if user_id not in context.bot_data['scores']:
            context.bot_data['scores'][user_id] = 0
        
        message = f"""
🎮 *Word Scramble*

Unscramble this word:

🔤 `{scrambled.upper()}`

📏 *Length:* {len(word)} letters

Type your answer below! 👇
"""
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    elif query.data == "hint":
        # Simulate /hint command
        user_id = query.from_user.id
        
        if user_id not in games:
            await query.edit_message_text(
                "❌ No active game! Send /play to start.",
                parse_mode='Markdown'
            )
            return
        
        game = games[user_id]
        word = game['word']
        revealed = game['revealed']
        
        unrevealed = [i for i in range(len(word)) if i not in revealed]
        
        if not unrevealed:
            await query.edit_message_text(
                f"🎯 All letters revealed!\n\nThe word is: `{word.upper()}`",
                parse_mode='Markdown'
            )
            return
        
        position = random.choice(unrevealed)
        revealed.add(position)
        game['hints_used'] += 1
        
        if 'scores' not in context.bot_data:
            context.bot_data['scores'] = {}
        context.bot_data['scores'][user_id] = context.bot_data['scores'].get(user_id, 0) - 1
        
        hint_display = get_hint(word, revealed)
        
        await query.edit_message_text(
            f"💡 *Hint:* `{hint_display}`\n\n"
            f"📊 Hints used: {game['hints_used']}\n\n"
            "Keep guessing! 👇",
            parse_mode='Markdown'
        )

def main():
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found!")
        return
    
    print("✅ Token found. Starting bot...")
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("hint", hint_command))
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CommandHandler("score", score_command))
    
    # Add message handler for guesses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🎮 Word Scramble Bot is running!")
    print("📱 Find your bot on Telegram and send /start")
    application.run_polling()

if __name__ == '__main__':
    main()
