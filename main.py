import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
import config
import market_data
import analysis
import risk
import database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=config.logger.level if hasattr(config, "logger") else logging.INFO,
)
logger = logging.getLogger(__name__)

def _menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton("📊 Signals", callback_data="signals"),
         InlineKeyboardButton("🔍 Analyze", callback_data="analyze")],
        [InlineKeyboardButton("💱 Pairs", callback_data="pairs"),
         InlineKeyboardButton("📈 Market", callback_data="market")],
        [InlineKeyboardButton("⚠️ Risk", callback_data="risk"),
         InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh")],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database.get_prefs(update.effective_user.id)
    text = (
        "🤖 **Forex Trading Bot**\n\n"
        "Algorithmic analysis only. Not financial advice. No profit guaranteed.\n\n"
        "Use /signals, /analyze, /price, /pairs, /market, /risk, /about, /status.\n"
        "Tap a button below:"
    )
    await update.message.reply_text(text, reply_markup=_menu(), parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start – Menu\n/help – This help\n/signals – Scan all pairs for signals\n"
        "/analyze – Analyze your saved pair\n/price – Latest price\n/pairs – Supported pairs\n"
        "/market – Data status\n/risk – Position size calculator (usage: /risk 1000 1 50 EUR/USD)\n"
        "/about – Disclaimer\n/status – Bot health\n/stop – Disable alerts",
        reply_markup=_menu(),
    )

async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not config.FOREX_API_KEY:
        await update.message.reply_text("⚠️ No market-data API key configured. Signals unavailable.")
        return
    msg = await update.message.reply_text("Scanning 8 pairs…")
    lines = []
    for pair in config.SUPPORTED_PAIRS:
        try:
            candles = await market_data.fetch_candles(pair, config.DEFAULT_TIMEFRAME)
            if market_data.is_stale(candles):
                lines.append(f"{pair}: ⚠️ Stale data")
                continue
            r = analysis.analyze(pair, candles)
            if r["decision"] != "NO TRADE":
                lines.append(
                    f"**{pair} {r['decision']}** @ {r['entry']}\n"
                    f"  SL {r['stop']} | TP1 {r['tp1']} | TP2 {r['tp2']} | RR {r['rr']}\n"
                    f"  {r['reason']}"
                )
            else:
                lines.append(f"{pair}: NO TRADE — {r['reason']}")
        except market_data.MarketDataError as e:
            lines.append(f"{pair}: ❌ {e}")
    await msg.edit_text("\n".join(lines), parse_mode="Markdown")

async def analyze_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = database.get_prefs(update.effective_user.id)
    pair = prefs["pair"]
    if not config.FOREX_API_KEY:
        await update.message.reply_text("⚠️ No API key. Cannot analyze.")
        return
    try:
        candles = await market_data.fetch_candles(pair, prefs["timeframe"])
        if market_data.is_stale(candles):
            await update.message.reply_text(f"⚠️ Data for {pair} is stale. Try later.")
            return
        r = analysis.analyze(pair, candles)
        text = f"**{pair} — {r['decision']}**\n"
        if r["decision"] == "NO TRADE":
            text += f"Reason: {r['reason']}"
        else:
            text += (
                f"Entry: {r['entry']}\nStop: {r['stop']}\nTP1: {r['tp1']}\nTP2: {r['tp2']}\n"
                f"RR: {r['rr']}\nATR: {r['atr']:.5f}\n\n{r['reason']}\n\n"
                f"Data: {prefs['timeframe']} candles | UTC. Algorithmic output, not advice."
            )
        await update.message.reply_text(text, parse_mode="Markdown")
    except market_data.MarketDataError as e:
        await update.message.reply_text(f"❌ {e}")

async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = database.get_prefs(update.effective_user.id)
    if not config.FOREX_API_KEY:
        await update.message.reply_text("⚠️ No API key. Price unavailable.")
        return
    try:
        candles = await market_data.fetch_candles(prefs["pair"], prefs["timeframe"], outputsize=10)
        latest = candles[0]
        await update.message.reply_text(
            f"**{prefs['pair']}**\nPrice: {latest['close']}\nTime (UTC): {latest['datetime']}\n"
            f"Source: Twelve Data | Free tier may be delayed.",
            parse_mode="Markdown",
        )
    except market_data.MarketDataError as e:
        await update.message.reply_text(f"❌ {e}")

async def pairs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Supported pairs:\n" + "\n".join(f"• {p}" for p in config.SUPPORTED_PAIRS)
    )

async def market_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not config.FOREX_API_KEY:
        await update.message.reply_text("Market data: ❌ Unavailable (no API key).")
        return
    await update.message.reply_text(
        f"Market data: ✅ Configured ({config.FOREX_API_PROVIDER})\n"
        f"Timeframe: {config.DEFAULT_TIMEFRAME}\n"
        f"Rate limit: 8 credits/min, 800/day (Basic free tier).\n"
        "Data may be delayed. Not for live execution."
    )

async def risk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 4:
        await update.message.reply_text(
            "Usage: /risk <balance> <risk%> <stop_pips> <pair>\n"
            "Example: /risk 1000 1 50 EUR/USD"
        )
        return
    try:
        balance = float(args[0]); risk_pct = float(args[1]); stop = float(args[2])
        pair = args[3].upper()
    except ValueError:
        await update.message.reply_text("Invalid numbers. Example: /risk 1000 1 50 EUR/USD")
        return
    if risk_pct > config.RISK_MAX_PERCENT:
        await update.message.reply_text(f"Risk % capped at {config.RISK_MAX_PERCENT}%.")
        return
    result = risk.calculate_position(balance, risk_pct, stop, pair)
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
    else:
        await update.message.reply_text(
            f"Risk amount: ${result['risk_amount']}\n"
            f"Approx. lot size: {result['lots']} lots\n"
            f"Pip value assumed: {result['pip_value']} USD\n"
            f"Note: {result['note']}"
        )

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "**Forex Trading Bot**\n\n"
        "Algorithmic technical analysis using EMA20/50, RSI14, MACD, ATR14 on closed 1h candles.\n"
        "Signals are NOT financial advice. No profit or accuracy is guaranteed.\n"
        "This bot does not execute trades. It does not request broker credentials.\n"
        "Data from Twelve Data free tier may be delayed.",
        parse_mode="Markdown",
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefs = database.get_prefs(update.effective_user.id)
    await update.message.reply_text(
        f"Bot: ✅ Online\n"
        f"Market data: {'✅ Configured' if config.FOREX_API_KEY else '❌ No API key'}\n"
        f"Your pair: {prefs['pair']} | Timeframe: {prefs['timeframe']}\n"
        f"Alerts: {'ON' if prefs['alerts'] else 'OFF'}"
    )

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    database.set_pref(update.effective_user.id, "alerts_enabled", 0)
    await update.message.reply_text("Alerts disabled. Use /start to re-enable via settings.")

async def button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data
    fake = type("U", (), {"message": q.message, "effective_user": q.from_user})()
    if data == "signals":
        await signals_cmd(fake, context)
    elif data == "analyze":
        await analyze_cmd(fake, context)
    elif data == "pairs":
        await pairs_cmd(fake, context)
    elif data == "market":
        await market_cmd(fake, context)
    elif data == "risk":
        await q.message.reply_text("Use /risk <balance> <risk%> <stop_pips> <pair>")
    elif data == "help":
        await help_cmd(fake, context)
    elif data == "refresh":
        await q.message.reply_text("Refreshed. Use a command or button.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Unknown command. Try /help.")

async def post_init(application) -> None:
    await application.bot.set_my_commands([
        ("start", "Menu"), ("help", "Help"), ("signals", "Scan for signals"),
        ("analyze", "Analyze saved pair"), ("price", "Latest price"),
        ("pairs", "Supported pairs"), ("market", "Market status"),
        ("risk", "Position size calculator"), ("about", "Disclaimer"),
        ("status", "Bot health"), ("stop", "Disable alerts"),
    ])

def main() -> None:
    database.init_db()
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("signals", signals_cmd))
    app.add_handler(CommandHandler("analyze", analyze_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("pairs", pairs_cmd))
    app.add_handler(CommandHandler("market", market_cmd))
    app.add_handler(CommandHandler("risk", risk_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(CommandHandler("__unknown__", unknown))
    logger.info("Bot starting with long polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
