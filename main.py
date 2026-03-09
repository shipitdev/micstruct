import os
import asyncio
import logging
from dotenv import load_dotenv

from src.state import SignalState
from src.stream import StreamManager
from src.telegram import TelegramManager
from src.brain import SniperBrain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Main")

# Load environment variables
load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
CHANNEL = os.getenv("TELEGRAM_CHANNEL")

if not all([API_ID, API_HASH, CHANNEL]):
    logger.error("Missing Telegram configuration in .env file.")
    # For now, we will use placeholders if .env is missing to allow initialization
    API_ID = int(API_ID) if API_ID else 0
    API_HASH = API_HASH or ""
    CHANNEL = CHANNEL or ""

class ClickinBot:
    def __init__(self):
        self.brain = SniperBrain()
        self.states: dict[str, SignalState] = {}
        self.stream_manager = None
        self.running_streams = set()

    async def on_signal(self, symbol, side, leverage, entry):
        symbol = symbol.upper()
        logger.info(f"New Signal Received: {symbol} {side} {leverage}x @ {entry}")
        
        # 1. Provide default TP/SL (e.g., TP at 1%, SL at 1% or as defined in brain)
        tp = entry * 1.01 if side.lower() == "long" else entry * 0.99
        self.brain.add_to_watchlist(symbol, side, leverage, entry, tp)

        # 2. Start stream if not already running
        if symbol not in self.running_streams:
            if symbol not in self.states:
                self.states[symbol] = SignalState()
            
            logger.info(f"Starting data stream for {symbol}...")
            asyncio.create_task(self.stream_manager.run_stream(symbol, self.states[symbol]))
            self.running_streams.add(symbol)

    async def run_brain_loop(self):
        """Main loop that updates the brain for all active symbols."""
        while True:
            # Update all symbols that are in watchlist or positions
            active_symbols = set(self.brain.active_watchlist.keys()) | set(self.brain.simulated_positions.keys())
            
            for symbol in list(active_symbols):
                if symbol in self.states:
                    self.brain.update(symbol, self.states[symbol])
            
            await asyncio.sleep(0.1)  # 100ms heartbeat

    async def start(self):
        # Initialize Managers
        self.stream_manager = StreamManager() 
        
        telegram_manager = TelegramManager(
            api_id=int(API_ID),
            api_hash=API_HASH,
            channel_id=CHANNEL,
            callback=self.on_signal
        )

        # Run Telegram and Brain Loop
        await asyncio.gather(
            telegram_manager.start(),
            self.run_brain_loop()
        )

if __name__ == "__main__":
    bot = ClickinBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
