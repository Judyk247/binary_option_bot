# strategy_runner.py

import time
import logging
from pocket_option import PocketOptionWS
from strategy import check_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class StrategyRunner:
    def __init__(self, symbol="EURUSD_otc", timeframe="M3"):
        """
        Strategy runner that connects Pocket Option WebSocket with trading strategy
        :param symbol: The asset/pair to trade (default EURUSD_otc)
        :param timeframe: Candle timeframe (default 3-minutes)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.ws = PocketOptionWS()

    def start(self):
        logging.info(f"Starting Strategy Runner for {self.symbol} on {self.timeframe} timeframe...")
        self.ws.connect()

        try:
            while True:
                # Fetch latest candle history from WebSocket
                candles = self.ws.get_candles(self.symbol, self.timeframe, limit=50)
                if candles:
                    # Run your strategy logic
                    signal = check_signal(candles)
                    if signal:
                        logging.info(f"Signal detected: {signal} for {self.symbol} ({self.timeframe})")
                        # TODO: send to Telegram or dashboard here
                    else:
                        logging.info("No valid signal detected")
                else:
                    logging.warning("No candles received yet...")

                time.sleep(5)  # small delay before checking again

        except KeyboardInterrupt:
            logging.info("Strategy runner stopped manually.")
        finally:
            self.ws.disconnect()


if __name__ == "__main__":
    runner = StrategyRunner(symbol="EURUSD_otc", timeframe="M3")
    runner.start()
