# dashboard.py
from flask import Flask, render_template, request, redirect, url_for
from trading_bot import candles_data, TIMEFRAMES, send_telegram_alert
from credentials import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from threading import Thread
import time
from datetime import datetime

app = Flask(__name__)

# In-memory approved signals
approved_signals = []  # List of dicts: {"symbol":.., "signal":.., "timeframe":.., "time":..}

def background_signal_checker():
    """Continuously check candles_data for signals and mark pending alerts."""
    while True:
        for tf, symbols in candles_data.items():
            for symbol, df in symbols.items():
                # The last candle could have produced a signal
                # For demo, assume trading_bot already analyzed candles and called analyze_candles
                # Here, we just track pending signals (not sent to Telegram yet)
                # In production, trading_bot sends alerts, or you can integrate approval here
                pass
        time.sleep(30)  # refresh every 30s

@app.route("/")
def index():
    """Main dashboard view"""
    display_data = []
    for tf, symbols in candles_data.items():
        for symbol, df in symbols.items():
            last_candle = df.iloc[-1] if not df.empty else None
            if last_candle is not None:
                display_data.append({
                    "symbol": symbol,
                    "timeframe": tf,
                    "last_close": last_candle["close"],
                    "last_open": last_candle["open"]
                })
    return render_template("dashboard.html", candles=display_data, approved=approved_signals, now=datetime.utcnow())

@app.route("/approve_signal", methods=["POST"])
def approve_signal():
    symbol = request.form.get("symbol")
    signal = request.form.get("signal")
    timeframe = request.form.get("timeframe")
    time_signal = datetime.utcnow()

    # Add to approved signals
    approved_signals.append({
        "symbol": symbol,
        "signal": signal,
        "timeframe": timeframe,
        "time": time_signal
    })

    # Send Telegram alert immediately after approval
    send_telegram_alert(symbol, signal, timeframe)

    return redirect(url_for("index"))

if __name__ == "__main__":
    # Start background thread for signal checking
    thread = Thread(target=background_signal_checker)
    thread.daemon = True
    thread.start()

    app.run(host="0.0.0.0", port=5000, debug=True)
