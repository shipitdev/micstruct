import asyncio
import logging
from src.state import SignalState
from src.brain import SniperBrain
from main import ClickinBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockTest")

async def mock_telegram_signal(bot):
    """Simulates a Telegram signal being received."""
    await asyncio.sleep(2) # Wait for bot to start
    logger.info("Simulating Telegram signal: #BTC/USDT - Long 20x | Entry: 50000.0")
    # In real life, TelegramManager calls this callback
    await bot.on_signal("BTC", "Long", 20, 50000.0)

async def main():
    bot = ClickinBot()
    
    # We need to override start to avoid Telegram connection
    bot.stream_manager = bot.stream_manager or __import__('src.stream').stream.StreamManager()
    
    # Create tasks
    tasks = [
        bot.run_brain_loop(),
        mock_telegram_signal(bot)
    ]
    
    logger.info("Starting mock integration test...")
    try:
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)
    except asyncio.TimeoutError:
        logger.info("Test finished (timeout).")
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
