import os
import logging
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

import database as db
import games

# ---------- CONFIG ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN env var missing!")

PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("Champion09Xbot")

# ---------- RAILWAY HEALTH SERVER ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Champion09Xbot is alive")
    def log_message(self, *a, **k): pass

def start_health_server():
    try:
        HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()
    except Exception as e:
        logger.warning(f"Health server error: {e}")

# ---------- KEYBOARDS ----------
def main_menu():
    kb = [
        [InlineKeyboardButton("🎯 Number Guess", callback_data="game_guess"),
         InlineKeyboardButton("🧮 Math Duel",   callback_data="game_math")],
        [InlineKeyboardButton("🎲 Dice Roll",   callback_data="game_dice"),
         InlineKeyboardButton("🪙 Coin Flip",   callback_data="game_coin")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("👤 Profile",     callback_data="profile")],
    ]
    return InlineKeyboardMarkup(kb)

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="menu")]])

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.ensure_user(u.id, u.username, u.first_name)
    games.cancel(update.effective_chat.id)
    await update.message.reply_text(
        f"🏆 *Welcome, {u.first_name}!*\n\n"
        "You've entered the *ChampionX Arena* — where legends are made.\n\n"
        "🎮 *Games available:*\n"
        "• Number Guess — guess 1–50\n"
        "• Math Duel — solve equations fast\n"
        "• Dice Roll — beat the bot\n"
        "• Coin Flip — call it in the air\n\n"
        "📈 Earn points, climb the leaderboard, become a Champion!\n\n"
        "Use the menu below 👇",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*ChampionX Bot Commands*\n\n"
        "• /start – Main menu & games\n"
        "• /play – Show games\n"
        "• /leaderboard – Top 10 Champions\n"
        "• /profile – Your stats\n"
        "• /cancel – Cancel current game\n"
        "• /help – This message\n\n"
        "⚠️ Play fair. Have fun!"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=back_menu())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())

async def play_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.ensure_user(u.id, u.username, u.first_name)
    await update.message.reply_text("🎮 *Choose your game:*",
                                    parse_mode="Markdown", reply_markup=main_menu())

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games.cancel(update.effective_chat.id)
    await update.message.reply_text("❌ Game cancelled.", reply_markup=back_menu())

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message or update.callback_query.message
    rows = db.top_global(10)
    if not rows:
        await target.reply_text("🏆 No champions yet — be the first to play!",
                                reply_markup=back_menu())
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🏆 *ChampionX Leaderboard*\n"]
    for i, r in enumerate(rows):
        name = r["first_name"] or r["username"] or "Champion"
        lines.append(f"{medals[i]} *{name}* — {r['points']} pts  ({r['wins']}W)")
    await target.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_menu())

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.ensure_user(u.id, u.username, u.first_name)
    target = update.message or update.callback_query.message
    row = db.get_user(u.id)
    rank = db.user_rank(u.id)
    win_rate = (row["wins"] / row["games"] * 100) if row["games"] else 0
    text = (
        f"👤 *{row['first_name']}*\n"
        f"🆔 `{row['user_id']}`\n\n"
        f"⭐ Points: *{row['points']}*\n"
        f"🏆 Wins: *{row['wins']}*\n"
        f"💀 Losses: *{row['losses']}*\n"
        f"🎮 Games: *{row['games']}*\n"
        f"📊 Win rate: *{win_rate:.1f}%*\n"
        f"🌍 Global rank: *#{rank}*"
    )
    await target.reply_text(text, parse_mode="Markdown", reply_markup=back_menu())

# ---------- BUTTON ROUTER ----------
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    u = q.from_user
    chat_id = q.message.chat_id
    db.ensure_user(u.id, u.username, u.first_name)

    if data == "menu":
        games.cancel(chat_id)
        await q.message.edit_text("🎮 *Main Menu*", parse_mode="Markdown",
                                  reply_markup=main_menu())
        return

    if data == "leaderboard":
        rows = db.top_global(10)
        if not rows:
            await q.message.edit_text("🏆 No champions yet — be the first to play!",
                                      reply_markup=back_menu())
            return
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        lines = ["🏆 *ChampionX Leaderboard*\n"]
        for i, r in enumerate(rows):
            name = r["first_name"] or r["username"] or "Champion"
            lines.append(f"{medals[i]} *{name}* — {r['points']} pts  ({r['wins']}W)")
        await q.message.edit_text("\n".join(lines), parse_mode="Markdown",
                                  reply_markup=back_menu())
        return

    if data == "profile":
        row = db.get_user(u.id)
        rank = db.user_rank(u.id)
        win_rate = (row["wins"] / row["games"] * 100) if row["games"] else 0
        text = (
            f"👤 *{row['first_name']}*\n🆔 `{row['user_id']}`\n\n"
            f"⭐ Points: *{row['points']}*\n🏆 Wins: *{row['wins']}*\n"
            f"💀 Losses: *{row['losses']}*\n🎮 Games: *{row['games']}*\n"
            f"📊 Win rate: *{win_rate:.1f}%*\n🌍 Global rank: *#{rank}*"
        )
        await q.message.edit_text(text, parse_mode="Markdown", reply_markup=back_menu())
        return

    # ---- GAME LAUNCHES ----
    if data == "game_guess":
        txt = games.start_guess(chat_id, u.id)
        await q.message.edit_text(txt + "\n\n_Send your guess as a message._",
                                  parse_mode="Markdown", reply_markup=back_menu())
        return

    if data == "game_math":
        txt = games.start_math(chat_id, u.id)
        await q.message.edit_text(txt + "\n\n_Send your answer as a message._",
                                  parse_mode="Markdown", reply_markup=back_menu())
        return

    if data == "game_dice":
        await q.message.edit_text(
            "🎲 *Dice Roll*\n\nRoll against the bot. Highest number wins!",
            parse_mode="Markdown", reply_markup=games.dice_keyboard())
        return

    if data == "dice_roll":
        won, msg, pts = games.roll_dice()
        db.add_points(u.id, pts, won is True)
        db.save_score("dice", u.id, pts)
        await q.message.edit_text(msg, parse_mode="Markdown", reply_markup=games.dice_keyboard())
        return

    if data == "game_coin":
        await q.message.edit_text(
            "🪙 *Coin Flip*\n\nCall it in the air!",
            parse_mode="Markdown", reply_markup=games.coin_keyboard())
        return

    if data in ("coin_heads", "coin_tails"):
        choice = data.split("_")[1]
        won, msg, pts = games.flip_coin(choice)
        db.add_points(u.id, pts, won is True)
        db.save_score("coin", u.id, pts)
        await q.message.edit_text(msg, parse_mode="Markdown", reply_markup=games.coin_keyboard())
        return

# ---------- TEXT HANDLER (for guess / math answers) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    u = update.effective_user
    if not update.message or not update.message.text:
        return
    if not games.is_active(chat_id):
        return
    db.ensure_user(u.id, u.username, u.first_name)

    text = update.message.text.strip()
    # try guess
    res = games.check_guess(chat_id, u.id, text)
    if res is None:
        res = games.check_math(chat_id, u.id, text)
    if res is None:
        return

    won, msg, pts = res
    if won is not None:
        db.add_points(u.id, pts, won is True)
        db.save_score("guess" if "Guess" in msg or "attempts" in msg else "math", u.id, pts)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=back_menu())

# ---------- ERROR HANDLER ----------
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception:", exc_info=context.error)
    logger.error("".join(traceback.format_exception(None, context.error,
                                                     context.error.__traceback__)))
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Try /start again.")
        except Exception:
            pass

# ---------- MAIN ----------
def main():
    db.init_db()
    logger.info("✅ Database initialised")

    threading.Thread(target=start_health_server, daemon=True).start()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("play", play_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CallbackQueryHandler(button_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(on_error)

    logger.info("🤖 @Champion09Xbot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
