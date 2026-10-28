import logging
import asyncio
import os
import sqlite3
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION ---
# Render will automatically inject your secrets here
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOREX_API_KEY = os.getenv("FOREX_API_KEY", "")
DB_PATH = "/tmp/forex_bot.db" 

if not BOT_TOKEN:
    raise ValueError("CRITICAL ERROR: TELEGRAM_BOT_TOKEN is missing in Render Environment Variables.")

SUPPORTED_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD", "EUR/GBP"]
TIMEFRAME = "1h"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS user_prefs (user_id INTEGER PRIMARY KEY, pair TEXT DEFAULT 'EUR/USD')")
    conn.commit()
    conn.close()

def get_pref(user_id):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    row = conn.execute("SELECT pair FROM user_prefs WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO user_prefs (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = ("EUR/USD",)
    conn.close()
    return row[0]

# --- MARKET DATA ---
async def fetch_candles(pair):
    if not FOREX_API_KEY:
        raise Exception("FOREX_API_KEY is missing in Render Environment Variables.")
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval={TIMEFRAME}&outputsize=100&apikey={FOREX_API_KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        data = resp.json()
        if data.get("status") == "error":
            raise Exception(data.get("message"))
        return data.get("values", [])

# --- INDICATORS & ANALYSIS ---
def calc_ema(closes, period):
    if len(closes) < period: return []
    k = 2 / (period + 1)
    out = [sum(closes[:period]) / period]
    for v in closes[period:]:
        out.append(v * k + out[-1] * (1 - k))
    return out

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag, al = sum(gains[-period:]) / period, sum(losses[-period:]) / period
    return 100.0 if al == 0 else 100 - (100 / (1 + ag / al))

def analyze_data(pair, candles):
    closes = [float(c["close"]) for c in reversed(candles)]
    e20, e50 = calc_ema(closes, 20), calc_ema(closes, 50)
    rsi = calc_rsi(closes)
    
    if not e20 or not e50: return "NO TRADE", "Not enough data."
    
    price = closes[-1]
    if e20[-1] > e50[-1] and 50 <= rsi <= 70:
        return "BUY", f"EMA20 > EMA50. RSI at {rsi:.1f}."
    elif e20[-1] < e50[-1] and 30 <= rsi <= 50:
        return "SELL", f"EMA20 < EMA50. RSI at {rsi:.1f}."
    else:
        return "NO TRADE", f"Trend unaligned. RSI at {rsi:.1f}."

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_pref(update.effective_user.id)
    kb = [
        [InlineKeyboardButton("📊 Signals", callback_data="signals"), InlineKeyboardButton("💱 Pairs", callback_data="pairs")],
        [InlineKeyboardButton("🔍 Analyze", callback_data="analyze"), InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    await update.message.reply_text("🤖 **Forex Bot Online**\nUse the buttons below:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands:\n/start\n/signals\n/analyze\n/price\n/pairs\n/risk\n/status")

async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FOREX_API_KEY:
        await update.message.reply_text("⚠️ No API key configured.")
        return
    msg = await update.message.reply_text("Scanning market...")
    lines = []
    for pair in SUPPORTED_PAIRS:
        try:
            candles = await fetch_candles(pair)
            decision, reason = analyze_data(pair, candles)
            lines.append(f"**{pair}**: {decision} - {reason}")
        except Exception as e:
            lines.append(f"**{pair}**: Error ({e})")
    await msg.edit_text("\n".join(lines), parse_mode="Markdown")

async def analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pair = get_pref(update.effective_user.id)
    try:
        candles = await fetch_candles(pair)
        decision, reason = analyze_data(pair, candles)
        await update.message.reply_text(f"**{pair}**\nDecision: {decision}\nReason: {reason}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pair = get_pref(update.effective_user.id)
    try:
        candles = await fetch_candles(pair)
        latest = candles[0]
        await update.message.reply_text(f"**{pair}**\nPrice: {latest['close']}\nTime: {latest['datetime']} UTC", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def pairs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Supported Pairs:\n" + ", ".join(SUPPORTED_PAIRS))

async def risk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usage: /risk 1000 1 50 EUR/USD\n(Account, Risk%, Stop Pips, Pair)\n\nResult: For $1000 at 1% risk, you can lose $10. With a 50 pip stop, lot size is 0.02.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "✅ Configured" if FOREX_API_KEY else "❌ Missing"
    await update.message.reply_text(f"Bot: Online\nAPI Key: {status}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fake_update = type("U", (), {"message": query.message, "effective_user": query.from_user})()
    if query.data == "signals": await signals_cmd(fake_update, context)
    elif query.data == "analyze": await analyze_cmd(fake_update, context)
    elif query.data == "pairs": await pairs_cmd(fake_update, context)
    elif query.data == "help": await help_cmd(fake_update, context)

def main():
    try: asyncio.get_event_loop()
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)

    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("signals", signals_cmd))
    app.add_handler(CommandHandler("analyze", analyze_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("pairs", pairs_cmd))
    app.add_handler(CommandHandler("risk", risk_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
