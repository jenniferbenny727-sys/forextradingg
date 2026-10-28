import time
import asyncio
import logging
from typing import Optional
import httpx

import config

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, dict]] = {}

class MarketDataError(Exception):
    pass

async def fetch_candles(pair: str, interval: str = "1h", outputsize: int = 200) -> list[dict]:
    cache_key = f"{pair}:{interval}:{outputsize}"
    now = time.time()
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < config.CACHE_TTL_SECONDS:
            return data["values"]

    if not config.FOREX_API_KEY:
        raise MarketDataError("FOREX_API_KEY not configured. Live data unavailable.")

    url = f"{config.API_BASE_URL}/time_series"
    params = {
        "symbol": pair,
        "interval": interval,
        "outputsize": str(outputsize),
        "apikey": config.FOREX_API_KEY,
        "timezone": "UTC",
    }

    last_exc = None
    for attempt in range(config.API_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=config.API_TIMEOUT_SECONDS) as client:
                resp = await client.get(url, params=params)
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning("Rate limited on %s, retry in %ss", pair, wait)
                await asyncio.sleep(wait)
                continue
            if resp.status_code != 200:
                raise MarketDataError(f"API HTTP {resp.status_code}")
            body = resp.json()
            if body.get("status") == "error":
                raise MarketDataError(body.get("message", "API error"))
            values = body.get("values")
            if not values or len(values) < 60:
                raise MarketDataError(f"Insufficient candles for {pair}: {len(values) if values else 0}")
            _cache[cache_key] = (now, {"values": values})
            return values
        except httpx.TimeoutException as e:
            last_exc = e
            logger.warning("Timeout on %s (attempt %d)", pair, attempt + 1)
        except httpx.HTTPError as e:
            last_exc = e
            logger.warning("HTTP error on %s: %s", pair, e)
        except MarketDataError:
            raise
    raise MarketDataError(f"Failed to fetch {pair} after retries: {last_exc}")

def is_stale(candles: list[dict]) -> bool:
    if not candles:
        return True
    latest = candles[0]
    try:
        from datetime import datetime, timezone
        dt = datetime.strptime(latest["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() > config.STALE_DATA_SECONDS
    except Exception:
        return True
