# data_fetcher.py
import asyncio
import json
import websockets
from credentials import POCKET_SESSION_TOKEN, POCKET_USER_ID, POCKET_ACCOUNT_URL
from collections import defaultdict
import time

# Store incoming data for all assets and timeframes
market_data = defaultdict(lambda: {"ticks": [], "candles": defaultdict(list)})

# Supported candle periods in seconds
CANDLE_PERIODS = [60, 120, 180, 300]  # 1m, 2m, 3m, 5m

async def subscribe_assets(ws):
    """Request assets list and subscribe to all active pairs"""
    # Request all assets
    await ws.send(json.dumps([42, ["getAssets", {}]]))
    
    while True:
        message = await ws.recv()
        if message.startswith("42"):
            data = json.loads(message[2:])
            event = data[0]
            payload = data[1] if len(data) > 1 else None

            if event == "assets":
                assets = [a["symbol"] for a in payload if a.get("enabled")]
                print(f"[SUBSCRIBE] Found {len(assets)} assets, subscribing...")

                for asset in assets:
                    # Subscribe to ticks
                    await ws.send(json.dumps([42, ["subscribe", {"type": "ticks", "asset": asset}]]))
                    # Subscribe to candles for all periods
                    for period in CANDLE_PERIODS:
                        await ws.send(json.dumps([42, ["subscribe", {"type": "candles", "asset": asset, "period": period}]]))
                return assets

async def process_message(message):
    """Process incoming WebSocket messages"""
    if not message.startswith("42"):
        return

    try:
        data = json.loads(message[2:])
        event = data[0]
        payload = data[1] if len(data) > 1 else None

        if event == "ticks" and payload:
            asset = payload["asset"]
            tick = {"time": payload["time"], "price": payload["price"]}
            market_data[asset]["ticks"].append(tick)

        elif event == "candles" and payload:
            asset = payload["asset"]
            period = payload["period"]
            candle = {
                "time": payload["time"],
                "open": payload["open"],
                "high": payload["high"],
                "low": payload["low"],
                "close": payload["close"],
                "volume": payload["volume"],
            }
            market_data[asset]["candles"][period].append(candle)

    except Exception as e:
        print("[ERROR parsing message]", e)

async def connect_pocket():
    url = "wss://ws.pocketoption.com/socket.io/?EIO=3&transport=websocket"
    while True:  # Auto-reconnect loop
        try:
            async with websockets.connect(url) as ws:
                # Authentication
                auth_message = [
                    42,
                    [
                        "auth",
                        {
                            "sessionToken": POCKET_SESSION_TOKEN,
                            "uid": POCKET_USER_ID,
                            "lang": "en",
                            "currentUrl": POCKET_ACCOUNT_URL,
                            "isChart": 1,
                        },
                    ],
                ]
                await ws.send(json.dumps(auth_message))
                print(f"[OPEN] Connected to Pocket Option ({POCKET_ACCOUNT_URL})")

                assets = await subscribe_assets(ws)

                # Listen to messages
                async for message in ws:
                    await process_message(message)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"[CLOSE] Connection lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[ERROR] {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

def get_market_data():
    """Return the latest market data snapshot"""
    return market_data

if __name__ == "__main__":
    asyncio.run(connect_pocket())
