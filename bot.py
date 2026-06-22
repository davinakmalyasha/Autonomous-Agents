"""
Telegram Bot — Entry point for the Virtual IT Office.
Handles text/voice input, routes through Jarvis, and runs the agentic pipeline.
"""
import os
import telebot
from dotenv import load_dotenv
from bot_helpers import transcribe_voice
from bot_runner import handle_build_request

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
bot = telebot.TeleBot(token)

@bot.message_handler(commands=["start", "help"])
def welcome(msg: telebot.types.Message) -> None:
    bot.reply_to(
        msg,
        "🏢 *Virtual IT Department*\n\n"
        "I can help you build, deploy, and analyze software projects autonomously. Send me a command to get started:\n"
        "• _\"Make a calculator app\"_ → Requirements + Design + Coder + QA\n"
        "• _\"Deploy my project to Railway\"_ → DevOps Setup\n"
        "• _\"Write requirements for a CRM\"_ → BA Specifications\n\n"
        "Ready to generate documentation, establish project environments, and build functional systems.",
        parse_mode="Markdown",
    )

_CHAT_KEYWORDS = {"hello", "hi", "hey", "thanks", "thank you", "good morning",
                  "good afternoon", "how are you", "what's up", "bye", "goodbye"}

def _is_obvious_chat(text: str) -> bool:
    import re
    text_lower = text.lower().strip()
    words = text_lower.rstrip(".!?").split()
    if len(words) > 6:
        return False
    
    # Greetings & thanks keyword check with word boundaries to avoid substring matches
    greetings = [
        r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bthanks\b", r"\bthank\s+you\b",
        r"\bgood\s+morning\b", r"\bgood\s+afternoon\b", r"\bhow\s+are\s+you\b",
        r"\bwhat's\s+up\b", r"\bbye\b", r"\bgoodbye\b"
    ]
    has_greeting = any(re.search(pattern, text_lower) for pattern in greetings)
    if not has_greeting:
        return False

    # Ensure it doesn't contain any task action words
    actions = [
        "build", "create", "make", "write", "code", "fix", "implement",
        "add", "change", "modify", "delete", "remove", "refactor", "deploy",
        "run", "test"
    ]
    has_action = any(re.search(rf"\b{act}\b", text_lower) for act in actions)
    return not has_action

@bot.message_handler(content_types=["text", "voice"])
def handle_request(msg: telebot.types.Message) -> None:
    chat_id = msg.chat.id
    status_msg = None

    if msg.content_type == "voice":
        status_msg = bot.send_message(chat_id, "🎙️ Transcribing voice...")
        req = transcribe_voice(bot, msg)
        if req.startswith("Error"):
            bot.edit_message_text(f"❌ {req}", chat_id, status_msg.message_id)
            return
        bot.edit_message_text(
            f"📝 Transcribed: \"{req}\"\n\n⏳ Processing...",
            chat_id, status_msg.message_id,
        )
    else:
        req = msg.text

    from chat_memory_manager import add_chat_message, resolve_request_text
    add_chat_message("user", req)

    # Clear failed models from previous requests
    try:
        from state_sync import safe_update_state
        safe_update_state({"failed_models": []})
    except Exception:
        pass

    resolved_req = resolve_request_text(req)

    # Quick chat check — no LLM call needed
    if _is_obvious_chat(req):
        add_chat_message("jarvis", "Hi! Ready to help. What do you need?")
        reply = "Hi! Ready to help. What do you need?"
        if status_msg:
            try:
                bot.edit_message_text(reply, chat_id, status_msg.message_id)
            except Exception:
                bot.send_message(chat_id, reply)
        else:
            bot.send_message(chat_id, reply)
        return

    # Go directly to the main agent
    add_chat_message("jarvis", f"Initiating work: {resolved_req}")

    if status_msg is None:
        status_msg = bot.send_message(chat_id, "⏳ Processing your request...")
    else:
        try:
            bot.edit_message_text("⏳ Processing your request...", chat_id, status_msg.message_id)
        except Exception:
            status_msg = bot.send_message(chat_id, "⏳ Processing your request...")

    handle_build_request(bot, resolved_req, chat_id, status_msg)

if __name__ == "__main__":
    print("[BOT] Telegram bot is running...")
    bot.infinity_polling()
