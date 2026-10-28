import os
import logging
from dotenv import load_dotenv

# Load the Secret File you created in Render
load_dotenv("/etc/secrets/.env")
load_dotenv() # Fallback for local testing

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOREX_API_KEY = os.getenv("FOREX_API_KEY")
FOREX_API_PROVIDER = os.getenv("FOREX_API_PROVIDER", "twelvedata")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing. Check your Render Secret Files or Environment Variables."
    )

if not FOREX_API_KEY:
    logger.warning(
        "FOREX_API_KEY is missing. Live market data will be unavailable. "
        "Basic commands will still work."
    )

# Using /tmp so SQLite works immediately without needing a paid disk
DB_PATH = os.getenv("DB_PATH", "/tmp/forex_bot.db")

API_BASE_URL = "https://api.twelvedata.com"
API_TIMEOUT_SECONDS = 10
API_MAX_RETRIES = 2
CACHE_TTL_SECONDS = 300
STALE_DATA_SECONDS = 7200

SUPPORTED_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
    "AUD/USD", "USD/CAD", "NZD/USD", "EUR/GBP",
]
DEFAULT_TIMEFRAME = "1h"
DEFAULT_PAIR = "EUR/USD"

RISK_DEFAULT_PERCENT = 1.0
RISK_MAX_PERCENT = 5.0
