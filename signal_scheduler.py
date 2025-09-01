# signal_scheduler.py
import time
import threading
from datetime import datetime, timedelta
from strategy import check_signals
from telegram_utils import send_telegram_alert
from data_fetcher import get_live_data

# timeframes in minutes
TIMEFRAMES = [1, 3, 5]

def get_next_candle_time(timeframe):
    """Return datetime for next candle close based on timeframe (in minutes)."""
    now = datetime.utcnow().replace(second=0, microsecond=0)
    minutes = (now.minute // timeframe + 1) * timeframe
    next_candle = now.replace(minute=minutes % 60, hour=(now.hour + minutes // 60) % 24)
    return next_candle

def schedule_signal(symbols):
    """Schedule signal checking and sending 30s before next candle."""
    def run():
        while True:
            for tf in TIMEFRAMES:
                next_candle = get_next_candle_time(tf)
                trigger_time = next_candle - timedelta(seconds=30)
                wait_seconds = (trigger_time - datetime.utcnow()).total_seconds()

                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                # fetch data and run strategy
                for symbol in symbols:
                    try:
                        df = get_live_data(symbol, tf)
                        if df is None or len(df) < 50:
                            continue
                        signal = check_signals(df, symbol, tf)
                        if signal:
                            send_telegram_alert(signal)
                    except Exception as e:
                        print(f"Error in {symbol} {tf}m: {e}")

            # short sleep before looping again
            time.sleep(1)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
