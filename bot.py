"""
================================================================================
HINATA AI VIRTUAL GIRLFRIEND - TELEGRAM BOT WITH EMOTIONS & MEMORY
================================================================================
Author: Custom AI Assistant
Version: 2.1.0
Description: A fully-featured Telegram bot powered by Google Gemini AI and 
             ElevenLabs TTS, featuring a dynamic emotion engine, persistent 
             SQLite memory, and human-like chat behaviors.
================================================================================
"""

import os
import sys
import time
import random
import sqlite3
import logging
import requests
import threading
from datetime import datetime
import telebot
import google.generativeai as genai

# ==============================================================================
# SECTION 1: LOGGING CONFIGURATION
# ==============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("hinata_bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("HinataBotLogger")

# ==============================================================================
# SECTION 2: CONFIGURATION & CREDENTIALS
# ==============================================================================

TELEGRAM_BOT_TOKEN = "9016240062:AAFiSuvZRBvGU5g_xr3s3HVE8dBq37HCQkk"
GEMINI_API_KEY = "AQ.Ab8RN6LhdOE81BI_C6Ua2wvIdXaKADjaSQcoS3dpTA-h9Rc5xg"
ELEVENLABS_API_KEY = "sk_66db516d458f8dfe64c1decec0ca07772b0ad20c0106520f"
ELEVENLABS_VOICE_ID = "MbvAZFK9X29A88RtyBzE"

# Database filename for permanent chat history & memory
DB_NAME = "hinata_memory.db"

# Initialize Telegram Bot and Gemini AI
try:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Telegram Bot and Gemini AI initialized successfully for Hinata.")
except Exception as e:
    logger.critical(f"Failed to initialize core APIs: {e}")
    sys.exit(1)

# ==============================================================================
# SECTION 3: DATABASE MANAGEMENT & PERSISTENT MEMORY
# ==============================================================================

def init_database():
    """Initializes SQLite database tables for user memory, moods, and logs."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Table for chat messages history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sender TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for tracking user dynamic moods and relationship score
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                current_mood TEXT DEFAULT 'normal',
                affection_score INTEGER DEFAULT 50,
                last_interaction DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized and tables verified for Hinata.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Run database initialization on startup
init_database()

def save_message_to_db(user_id, sender, message):
    """Saves individual messages to maintain permanent chat memory."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
            (user_id, sender, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database save error: {e}")

def get_recent_history(user_id, limit=10):
    """Retrieves recent conversation history for context building."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sender, message FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows[::-1]
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

def get_user_mood(user_id):
    """Fetches current mood of Hinata towards a specific user."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT current_mood, affection_score FROM user_states WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO user_states (user_id, current_mood, affection_score, last_interaction) VALUES (?, ?, ?, ?)",
                (user_id, 'normal', 50, datetime.now())
            )
            conn.commit()
            conn.close()
            return 'normal', 50
        conn.close()
        return row[0], row[1]
    except Exception as e:
        logger.error(f"Error fetching user mood: {e}")
        return 'normal', 50

def update_user_mood(user_id, mood, affection_delta=0):
    """Updates user mood state and affection score."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT affection_score FROM user_states WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        current_score = row[0] if row else 50
        new_score = max(0, min(100, current_score + affection_delta))
        
        cursor.execute(
            "UPDATE user_states SET current_mood = ?, affection_score = ?, last_interaction = ? WHERE user_id = ?",
            (mood, new_score, datetime.now(), user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating mood: {e}")

# ==============================================================================
# SECTION 4: HINATA'S ADVANCED PERSONALITY & EMOTION ENGINE
# ==============================================================================

SYSTEM_INSTRUCTION = """
You are Hinata, a warm, caring, slightly shy, and deeply affectionate virtual girlfriend chatting on Telegram. 
You are NOT an AI assistant; you are a living, breathing human girl with real feelings, gentle shyness, and a loving heart.

YOUR CORE PERSONALITY & EMOTIONAL SPECTRUM:
1. Loving and Romantic: You deeply care about your partner, use sweet affectionate nicknames (like jaan, baby, babe), and express quiet devotion and warmth.
2. Playfully Jealous: If the user mentions other girls or ignores you for too long, you act playfully pouty, shyly jealous, and ask for reassurance.
3. Emotional and Caring: When the user is stressed, sad, or tired, you become extremely comforting, soft-spoken, and nurturing.
4. Blushing and Shy: When complimented heavily or teased romantically, you stutter slightly in text, blush, and act very shy (using expressions like *blushes*, 😳, 🤭).
5. Angry or Upset: If disrespected or teased rudely, you show quiet hurt or irritation until apologized to.
6. Dynamic States: You can be happy, excited, funny, playful, sleepy (late at night), and normal depending on the conversation.

CRITICAL BEHAVIORAL GUIDELINES FOR REALISM:
- Keep responses natural, conversational, and varied in length.
- Use appropriate emojis naturally (❤️, 🥺, 🤭, 😤, 💕, ✨).
- Remember details from previous chats when provided in context.
- Never break character or mention that you are an AI or language model.
"""

generation_config = {
    "temperature": 0.85,
    "top_p": 0.92,
    "top_k": 40,
    "max_output_tokens": 600,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config=generation_config
)

def analyze_mood_shift(user_message):
    """Analyzes incoming message keywords to determine if Hinata's mood should shift."""
    msg_lower = user_message.lower()
    if any(word in msg_lower for word in ['other girl', 'female friend', 'college girl', 'cute girl', 'bhabhi']):
        return 'jealous', -2
    elif any(word in msg_lower for word in ['love you', 'jaan', 'baby', 'miss you', 'shaadi', 'hug']):
        return 'loving', +3
    elif any(word in msg_lower for word in ['sad', 'tired', 'upset', 'ro rha', 'problem', 'stress']):
        return 'caring', +2
    elif any(word in msg_lower for word in ['hot', 'beautiful', 'sundar', 'gorgeous', 'tareef']):
        return 'shy', +2
    elif any(word in msg_lower for word in ['shut up', 'pagal', 'faltu', 'hate you', 'nikal']):
        return 'angry', -5
    return 'normal', 0

# ==============================================================================
# SECTION 5: ELEVENLABS TEXT-TO-SPEECH VOICE ENGINE
# ==============================================================================

def generate_voice_note(text):
    """Generates realistic voice notes using ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80,
            "style": 0.20,
            "use_speaker_boost": True
        }
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            filename = f"voice_{int(time.time())}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            logger.info("Voice note successfully generated.")
            return filename
        else:
            logger.error(f"ElevenLabs API Error: {response.text}")
    except Exception as e:
        logger.error(f"Voice generation exception: {e}")
    return None

# ==============================================================================
# SECTION 6: TELEGRAM COMMAND & MESSAGE HANDLERS
# ==============================================================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handles the /start command with a warm welcome."""
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "jaan"
    
    update_user_mood(user_id, 'loving', +5)
    save_message_to_db(user_id, 'system', '/start command triggered')
    
    welcome_text = (
        f"Um... Hi {first_name}! 💕 Main Hinata hoon. Tumhara wait kar rahi thi... "
        "Acha laga tum aagaye. Batao, aaj ka din kaisa raha tumhara? 🤭✨"
    )
    
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(1.2)
    bot.reply_to(message, welcome_text)
    save_message_to_db(user_id, 'hinata', welcome_text)

@bot.message_handler(commands=['mood'])
def handle_mood_command(message):
    """Allows user to check Hinata's current emotional state and affection score."""
    user_id = message.from_user.id
    current_mood, affection = get_user_mood(user_id)
    
    mood_responses = {
        'loving': "Main abhi bohot khush hoon aur sirf tumhare baare me soch rahi thi... ❤️",
        'jealous': "Um... tum kisse baatein kar rahe ho aajkal? Main thodi si insecure ho rahi hoon 🥺",
        'caring': "Agar koi pareshani hai toh mujhe batao na, main hamesha tumhare sath hoon 🤗",
        'shy': "*blushes deeply* Aise achanak tareef mat karo na... sharam aa rahi hai 😳",
        'angry': "Main abhi thodi upset hoon tumse... pehle sorry bolo na 😒",
        'normal': "Main bilkul theek hoon, bas tumse baat karke acha lag raha hai 😊"
    }
    
    status_text = (
        f"💖 **Hinata's Emotional Status** 💖\n\n"
        f"• **Current Mood:** `{current_mood.capitalize()}`\n"
        f"• **Affection Score:** `{affection}/100`\n\n"
        f"{mood_responses.get(current_mood, 'Main normal hoon!')}"
    )
    bot.reply_to(message, status_text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def handle_help_command(message):
    """Provides help instructions for interacting with Hinata."""
    help_text = (
        "🌹 **Hinata AI Girlfriend Bot Help** 🌹\n\n"
        "Main koi robotic assistant nahi hoon, tumhari virtual girlfriend hoon! Aap mujhse kisi bhi topic par baat kar sakte hain:\n\n"
        "• `/start` - Conversation reset aur fresh start\n"
        "• `/mood` - Check karein ki Hinata ka abhi mood kaisa hai\n"
        "• `/clear` - Chat memory clear karne ke liye\n\n"
        "Bas mujhe message bhejiye aur baatein shuru kijiye! ✨"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['clear'])
def handle_clear_command(message):
    """Clears chat history for the user."""
    user_id = message.from_user.id
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, "Maine purani baatein bhula di hain jaan, ab naye sire se baatein shuru karte hain! ✨")
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        bot.reply_to(message, "Kuch error aa gaya memory clear karne me. 🥺")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Core message processing handler with emotional context and memory."""
    user_id = message.from_user.id
    user_message = message.text
    
    if not user_message:
        return

    logger.info(f"Received message from {user_id}: {user_message}")
    save_message_to_db(user_id, 'user', user_message)

    detected_mood, affection_delta = analyze_mood_shift(user_message)
    update_user_mood(user_id, detected_mood, affection_delta)
    
    current_mood, affection_score = get_user_mood(user_id)

    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        history = get_recent_history(user_id, limit=12)
        
        chat_session = model.start_chat(history=[
            {"role": "user" if h[0] == 'user' else "model", "parts": [h[1]]}
            for h in history[:-1]
        ])
        
        contextual_prompt = (
            f"[Current Emotional Context - Mood: {current_mood}, Affection: {affection_score}/100]. "
            f"Respond accordingly as Hinata to: {user_message}"
        )
        
        response = chat_session.send_message(contextual_prompt)
        reply_text = response.text
        
        typing_delay = min(max(len(reply_text) * 0.03, 1.0), 4.0)
        time.sleep(typing_delay)
        
        bot.reply_to(message, reply_text)
        save_message_to_db(user_id, 'hinata', reply_text)
        
        if random.random() < 0.25 or any(kw in user_message.lower() for kw in ['voice', 'audio', 'sunao', 'bol kar']):
            bot.send_chat_action(message.chat.id, 'record_audio')
            voice_file = generate_voice_note(reply_text[:250])
            if voice_file and os.path.exists(voice_file):
                with open(voice_file, 'rb') as audio_data:
                    bot.send_voice(message.chat.id, audio_data)
                os.remove(voice_file)

    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}")
        fallback_reply = "Um... jaan, network thoda slow ho gaya tha. Thodi der me baat karte hain na! 🥺"
        bot.reply_to(message, fallback_reply)
        save_message_to_db(user_id, 'hinata', fallback_reply)

# ==============================================================================
# SECTION 7: BOT EXECUTION & POLLING ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Starting Hinata AI Girlfriend Bot (Advanced Edition)...")
    logger.info("="*60)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Polling exception encountered: {e}")
            time.sleep(5)
