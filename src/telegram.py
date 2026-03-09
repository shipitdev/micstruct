import asyncio
import re
import logging
from typing import Callable, Optional, Union
from telethon import TelegramClient, events

# Configuration for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramManager")


class TelegramManager:
    """Monitors Telegram channels for trading signals using the Telethon library.

    This manager listens for new messages in a specified channel, parses signals 
    matching a specific format via Regex, and triggers a callback for downstream 
    processing (e.g., adding to a watchlist).

    Attributes:
        api_id (int): Telegram API ID.
        api_hash (str): Telegram API Hash.
        channel_id (Union[str, int]): Username or ID of the channel to monitor.
        callback (Callable): Async or sync function to call when a signal is found.
    """

    def __init__(
        self, 
        api_id: int, 
        api_hash: str, 
        channel_id: Union[str, int], 
        callback: Callable
    ) -> None:
        """Initializes the TelegramManager with credentials and signal routing.

        Args:
            api_id (int): Your Telegram API ID.
            api_hash (str): Your Telegram API Hash.
            channel_id (Union[str, int]): Channel username (e.g., '@Signals') or ID.
            callback (Callable): Logic to execute on valid signals.
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.channel_id = channel_id
        self.callback = callback
        
        # Session name 'bot_signal_session' will create a .session file locally
        self.client = TelegramClient('bot_signal_session', api_id, api_hash)

        # Regex pattern for: "| Coin: #SYMBOL/USDT - Side Leverage | Entry: PRICE Targets: TP1, TP2..."
        # Example Match: | Coin: #PHA/USDT - Long 20x | Entry: 0.1234
        self.signal_pattern = re.compile(
            r"\|\s*Coin:\s*#(\w+)/USDT\s*-\s*(Long|Short)\s*(\d+)x\s*\|\s*Entry\s*(?:Targets)?:\s*([\d.]+)",
            re.IGNORECASE | re.DOTALL
        )

    async def start(self) -> None:
        """Connects the Telegram client and registers the message event handler."""
        logger.info(f"Connecting to Telegram... Monitoring channel: {self.channel_id}")
        
        # This will prompt for phone number/code in the terminal if no session exists
        await self.client.start()

        @self.client.on(events.NewMessage(chats=self.channel_id))
        async def new_message_handler(event: events.NewMessage.Event):
            await self._process_message(event.message.message)

        logger.info("Telegram client is now online and listening for signals.")
        await self.client.run_until_disconnected()

    async def _process_message(self, text: Optional[str]) -> None:
        """Parses incoming message text and routes valid signals to the callback.

        Args:
            text (Optional[str]): The raw message text from Telegram.
        """
        if not text:
            return

        match = self.signal_pattern.search(text)
        if match:
            try:
                symbol = match.group(1).upper()
                side = match.group(2).capitalize()
                leverage = int(match.group(3))
                entry_price = float(match.group(4))

                logger.info(f"Parsed Signal -> {symbol} | {side} | {leverage}x | Entry: {entry_price}")

                # Execute callback (handle both sync and async callbacks)
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(symbol, side, leverage, entry_price)
                else:
                    self.callback(symbol, side, leverage, entry_price)

            except (ValueError, IndexError) as e:
                logger.error(f"Error processing matched signal fields: {e}")
        else:
            # If the message doesn't match the format, we log it as a warning and skip
            # This avoids noise from channel chatter or unrelated updates
            logger.warning(f"Format mismatch. Ignored message: {text[:60].strip()}...")


# --- Configuration Placeholders ---
# API_ID = 1234567
# API_HASH = 'your_api_hash_here'
# CHANNEL = '@YourSignalChannel'
