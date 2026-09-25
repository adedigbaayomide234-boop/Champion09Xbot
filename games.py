import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ---------- Active game state (in-memory per chat) ----------
active = {}     # chat_id -> {"type":..., "user_id":..., "answer":..., "attempts":...}

def cancel(chat_id: int):
    active.pop(chat_id, None)

def is_active(chat_id: int):
    return chat_id in active

# ---------- Number Guess ----------
def start_guess(chat_id: int, user_id: int):
    answer = random.randint(1, 50)
    active[chat_id] = {"type": "guess", "user_id": user_id,
                       "answer": answer, "attempts": 0}
    return ("🎯 *Number Guess*\n\nI'm thinking of a number between *1 and 50*.\n"
            "Send me your guess!")

def check_guess(chat_id: int, user_id: int, text: str):
    game = active.get(chat_id)
    if not game or game["type"] != "guess":
        return None
    if game["user_id"] != user_id:
        return None
    try:
        n = int(text)
    except ValueError:
        return None
    game["attempts"] += 1
    if n == game["answer"]:
        pts = max(5, 20 - game["attempts"] * 2)
        active.pop(chat_id, None)
        return (True, f"🎉 *Correct!* The number was *{game['answer']}*.\n"
                       f"You earned *{pts} points* in *{game['attempts']}* attempts!", pts)
    if game["attempts"] >= 7:
        active.pop(chat_id, None)
        return (False, f"😢 Out of attempts! The number was *{game['answer']}*.", 0)
    hint = "⬆️ Higher!" if n < game["answer"] else "⬇️ Lower!"
    return (None, f"{hint} (attempt {game['attempts']}/7)", 0)

# ---------- Math Duel ----------
def start_math(chat_id: int, user_id: int):
    a, b = random.randint(2, 20), random.randint(2, 20)
    op = random.choice(["+", "-", "*"])
    if op == "+": ans = a + b
    elif op == "-": ans = a - b
    else: ans = a * b
    active[chat_id] = {"type": "math", "user_id": user_id, "answer": ans, "attempts": 0}
    return f"🧮 *Math Duel*\n\nWhat is *{a} {op} {b}* ?\nAnswer within 20 seconds!"

def check_math(chat_id: int, user_id: int, text: str):
    game = active.get(chat_id)
    if not game or game["type"] != "math":
        return None
    if game["user_id"] != user_id:
        return None
    try:
        n = int(text)
    except ValueError:
        return None
    active.pop(chat_id, None)
    if n == game["answer"]:
        return (True, f"✅ *Correct!* Answer was *{game['answer']}*. +15 points!", 15)
    return (False, f"❌ Wrong! The answer was *{game['answer']}*.", 0)

# ---------- Dice Roll ----------
def dice_keyboard():
    kb = [[InlineKeyboardButton("🎲 Roll Dice", callback_data="dice_roll")]]
    return InlineKeyboardMarkup(kb)

def roll_dice():
    user_roll = random.randint(1, 6)
    bot_roll  = random.randint(1, 6)
    if user_roll > bot_roll:
        return (True, f"🎲 You: *{user_roll}*  |  🤖 Bot: *{bot_roll}*\n\n🏆 *You win!* +10 points", 10)
    if user_roll < bot_roll:
        return (False, f"🎲 You: *{user_roll}*  |  🤖 Bot: *{bot_roll}*\n\n😢 You lose.", 0)
    return (None, f"🎲 You: *{user_roll}*  |  🤖 Bot: *{bot_roll}*\n\n🤝 Draw! +3 points", 3)

# ---------- Coin Flip ----------
def coin_keyboard():
    kb = [[
        InlineKeyboardButton("🪙 Heads", callback_data="coin_heads"),
        InlineKeyboardButton("🪙 Tails", callback_data="coin_tails"),
    ]]
    return InlineKeyboardMarkup(kb)

def flip_coin(choice: str):
    result = random.choice(["heads", "tails"])
    won = (choice == result)
    if won:
        return (True, f"🪙 It landed on *{result.upper()}*!\n\n🏆 *You win!* +8 points", 8)
    return (False, f"🪙 It landed on *{result.upper()}*.\n\n😢 Better luck next time!", 0)
