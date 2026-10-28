# Forex Trading Bot

Telegram bot for algorithmic forex analysis. **Not financial advice. No profit guaranteed.**

## Stack
- Python 3.11+
- python-telegram-bot v22.1 (async, long polling)
- Twelve Data free tier (8 credits/min, 800/day)
- SQLite on Render persistent disk

## Local test
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, fill `TELEGRAM_BOT_TOKEN` and `FOREX_API_KEY`.
3. Set `DB_PATH=./test.db` (local) or create `/var/data` (Render path).
4. `python main.py`

## Deploy to Render
1. Push all files to a GitHub repo.
2. Render Dashboard → New → Blueprint → connect repo.
3. `render.yaml` creates a **Background Worker** (paid, $7/mo minimum) with a 1 GB disk.
4. Set `TELEGRAM_BOT_TOKEN` and `FOREX_API_KEY` in Environment (marked `sync: false`).
5. Deploy. Check Logs for `Bot starting with long polling…`.

### Common errors
- `TELEGRAM_BOT_TOKEN is missing` → env var not set.
- `FOREX_API_KEY not configured` → bot runs but market commands return warnings.
- `MarketDataError: API HTTP 429` → Twelve Data rate limit. Wait 1 minute (8 credits/min).
- Disk not mounted → SQLite writes go to ephemeral storage; verify `mountPath: /var/data`.

## Limitations
- Twelve Data Basic: 8 credits/min. `/signals` checks 8 pairs = 8 credits, exactly at limit.
- No broker execution. No user credentials requested.
- Risk calculator uses fixed 10 USD/pip for USD pairs; other pairs return an error instead of misleading precision.
