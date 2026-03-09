import asyncio
import json
import logging
from typing import Any, Dict
import websockets

from src.state import SignalState

# Configure basic logging for the StreamManager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StreamManager")


class StreamManager:
    """Manages high-frequency data ingestion from Binance WebSockets.

    This class handles subscriptions to order book and trade streams,
    parsing incoming JSON data into the SignalState container with
    automatic reconnection logic.

    Attributes:
        url (str): Binance WebSocket base URL.
    """
    def __init__(self) -> None:
        """Initializes the StreamManager."""
        self.url = "wss://stream.binance.com:9443/ws"

    async def run_stream(self, symbol: str, state: SignalState) -> None:
        """Connects to Binance and maintains the data stream for a symbol.

        Args:
            symbol (str): The trading pair symbol (e.g., 'btcusdt').
            state (SignalState): The state object where market data is stored.
        """
        symbol = symbol.lower()
        subscribe_payload = {
            "method": "SUBSCRIBE",
            "params": [
                f"{symbol}@aggTrade",
                f"{symbol}@depth@100ms"
            ],
            "id": 1
        }

        while True:
            try:
                async with websockets.connect(self.url) as websocket:
                    logger.info(f"Connected to Binance. Subscribing to {symbol}...")
                    await websocket.send(json.dumps(subscribe_payload))

                    async for message in websocket:
                        data = json.loads(message)
                        self._process_message(data, state)

            except (websockets.ConnectionClosed, Exception) as e:
                logger.error(f"WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def _process_message(self, data: Dict[str, Any], state: SignalState) -> None:
        """Parses and dispatches incoming WebSocket messages to the state.

        Args:
            data (Dict[str, Any]): The parsed JSON message.
            state (SignalState): The state object to update.
        """
        event_type = data.get("e")

        if event_type == "aggTrade":
            # Binance aggTrade mapping:
            # 'E' -> Event time (ms)
            # 'm' -> Is the buyer the market maker? 
            #        If True: Buyer is Maker, Seller is Taker -> 'sell'
            #        If False: Seller is Maker, Buyer is Taker -> 'buy'
            # 'q' -> Quantity
            event_time = data["E"] / 1000.0
            side = "sell" if data["m"] else "buy"
            quantity = float(data["q"])
            
            state.add_trade(event_time, side, quantity)

        elif event_type == "depthUpdate":
            # 'b' -> bids list [price_str, qty_str]
            # 'a' -> asks list [price_str, qty_str]
            for price_str, qty_str in data.get("b", []):
                state.update_book("bid", float(price_str), float(qty_str))
            
            for price_str, qty_str in data.get("a", []):
                state.update_book("ask", float(price_str), float(qty_str))
