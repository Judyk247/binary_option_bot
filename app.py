# app.py
import threading
import time
from flask import Flask, render_template
from data_fetcher import get_live_data
from strategy import generate_signals
from telegram_utils import send_telegram_message
from config import SYMBOLS, TIMEFRAMES, TELEGRAM_CHAT_IDS

app = Flask(__name__)

latest_signals = {}

def fetch_and_generate():
    """Fetch data and generate signals continuously."""
    global latest_signals

    while True:
        try:
            signals = {}
            for symbol in SYMBOLS:
                signals[symbol] = {}
                for tf in TIMEFRAMES:
                    data = get_live_data(symbol, tf, length=50)
                    if not data.empty:
                        signal = generate_signals(data, symbol, tf)
                        signals[symbol][tf] = signal

                        # Send signal 30s before next candle close
                        if signal and "No Signal" not in signal:
                            now = time.time()
                            seconds_into_candle = int(now) % (int(tf[:-1]) * 60)
                            if seconds_into_candle >= (int(tf[:-1]) * 60 - 30):
                                for chat_id in TELEGRAM_CHAT_IDS:
                                    send_telegram_message(chat_id, signal)

            latest_signals = signals
        except Exception as e:
            print("Error fetching/generating signals:", str(e))

        time.sleep(30)  # check every 30s

@app.route("/")
def dashboard():
    return render_template("dashboard.html", signals=latest_signals)

if __name__ == "__main__":
    # Background thread for fetching data & generating signals
    t = threading.Thread(target=fetch_and_generate, daemon=True)
    t.start()
    
    app.run(host="0.0.0.0", port=5000, debug=False)
