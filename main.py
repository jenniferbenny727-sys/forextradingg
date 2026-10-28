
import logging
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Get the token securely from Render Environment Variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Reduce unnecessary HTTP logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 Forex Analysis", callback_data="analysis"),
            InlineKeyboardButton("💱 Currency Pairs", callback_data="pairs"),
        ],
        [
            InlineKeyboardButton("🛡️ Risk Management", callback_data="risk"),
            InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message

    if message:
        await message.reply_text(
            "🤖 Welcome to Forex Trading Bot!\n\n"
            "Your personal Forex assistant is online.\n\n"
            "Choose an option below to get started.\n\n"
            "⚠️ This initial version does not yet provide "
            "verified live prices or trading signals.",
            reply_markup=main_menu(),
        )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message

    if message:
        await message.reply_text(
            "📘 Forex Trading Bot Help\n\n"
            "/start - Open the main menu\n"
            "/help - Show this help message\n"
            "/status - Check whether the bot is running\n\n"
            "Live market analysis and trading signals "
            "require a market-data provider and a tested strategy."
        )


async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.effective_message

    if message:
        await message.reply_text(
            "✅ The bot is running and responding to commands.\n\n"
            "Market data: Not configured\n"
            "Live signals: Not enabled"
        )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    await query.answer()

    if query.data == "analysis":
        response = (
            "📊 Forex Analysis\n\n"
            "Live analysis is not configured yet. "
            "A market-data API and technical-analysis strategy "
            "must be added before real signals can be generated."
        )

    elif query.data == "pairs":
        response = (
            "💱 Supported pairs to configure:\n\n"
            "EUR/USD\n"
            "GBP/USD\n"
            "USD/JPY\n"
            "USD/CHF\n"
            "AUD/USD\n"
            "USD/CAD\n\n"
            "Live prices are not available yet."
        )

    elif query.data == "risk":
        response = (
            "🛡️ Risk Management\n\n"
            "Always define your stop loss before entering a trade. "
            "Avoid risking money you cannot afford to lose.\n\n"
            "Position-size calculations are not enabled yet."
        )

    elif query.data == "help":
        response = (
            "ℹ️ Commands\n\n"
            "/start - Main menu\n"
            "/help - Help information\n"
            "/status - Bot status"
        )

    else:
        response = "Unknown option. Please send /start."

    await query.message.reply_text(
        response,
        reply_markup=main_menu(),
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    logger.error(
        "An error occurred while processing an update.",
        exc_info=context.error,
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing. "
            "Add it in your Render Environment settings."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    logger.info("Forex Trading Bot is starting...")

    # run_polling manages its own event loop.
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
