from flask import Flask, render_template, request
from data_fetcher import fetch_batch, DEFAULT_SYMBOLS
from strategy import evaluate_trend_reversal_5m, evaluate_trend_following

app = Flask(__name__)

# Which symbols to show by default (edit freely)
SYMBOLS = DEFAULT_SYMBOLS

TIMEFRAMES = ["1m", "2m", "3m", "5m"]  # Columns in the dashboard

def evaluate_signals(data):
    """
    data: nested dict data[symbol][interval] = DataFrame
    Returns a dict of rows for template rendering:
    rows = [
      { 'symbol': 'EUR/USD', '1m': {'BUY':False,'SELL':True}, '2m':..., '3m':..., '5m':... },
      ...
    ]
    """
    rows = []
    for sym in data:
        row = {"symbol": sym}
        for tf in TIMEFRAMES:
            df = data[sym].get(tf)
            if df is None or df.empty or len(df) < 160:
                row[tf] = {"BUY": False, "SELL": False}
                continue

            if tf == "5m":
                sig = evaluate_trend_reversal_5m(df)
            else:
                sig = evaluate_trend_following(df)
            row[tf] = sig
        rows.append(row)
    return rows

@app.route("/")
def dashboard():
    # Optionally accept comma-separated ?symbols=EUR/USD,GBP/USD
    symbols_param = request.args.get("symbols")
    symbols = [s.strip() for s in symbols_param.split(",")] if symbols_param else SYMBOLS

    # Fetch data (web-service only; no background worker)
    market_data = fetch_batch(symbols, intervals=TIMEFRAMES, outputsize=200)

    # Evaluate signals
    rows = evaluate_signals(market_data)

    return render_template("dashboard.html", rows=rows, timeframes=TIMEFRAMES)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
