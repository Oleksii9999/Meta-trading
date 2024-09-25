
import MetaTrader5 as mt5
import time
from datetime import datetime
import telegram
import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
ACCOUNT_NUMBER = '1510022050'
PASSWORD = '!3x@1X7r'
SERVER = 'FTMO-Demo'
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID'
MAX_RISK_PER_TRADE = 4000  # $4,000 max risk per trade
NUM_ORDERS = 12

signal = {
    'symbol': 'XAUUSD',
    'type': 'buy',
    'entry_ranges': [(2656.0, 2652.0)],
    'tp_levels': [2659.0, 2662.0, 2665.0, open],
    'sl': 2649.0
}

def initialize_mt5():
    try:
        if not mt5.initialize():
            logger.error(f"initialize() failed, error code = {mt5.last_error()}")
            return False
        
        if not mt5.login(account=ACCOUNT_NUMBER, password=PASSWORD, server=SERVER):
            logger.error(f"login() failed, error code = {mt5.last_error()}")
            return False
        
        return True
    except Exception as e:
        logger.exception(f"Error initializing MT5: {e}")
        return False

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
def calculate_lot_size(entry_price, sl_price, max_risk_per_trade, num_orders):
    try:
        account_info = mt5.account_info()
        if account_info is None:
            raise ValueError("Failed to get account info")
        
        symbol_info = mt5.symbol_info(signal['symbol'])
        if symbol_info is None:
            raise ValueError(f"Failed to get symbol info for {signal['symbol']}")
        
        point = symbol_info.point
        sl_points = abs(entry_price - sl_price) / point
        tick_value = symbol_info.trade_tick_value
        
        max_loss_per_order = max_risk_per_trade / num_orders
        lot_size = max_loss_per_order / (sl_points * tick_value)
        
        return round(lot_size, 2)
    except Exception as e:
        logger.exception(f"Error calculating lot size: {e}")
        return None

def place_order(symbol, lot_size, order_type, entry_price, sl, tp):
    try:
        if order_type == 'buy':
            order = mt5.ORDER_TYPE_BUY_LIMIT
        else:
            order = mt5.ORDER_TYPE_SELL_LIMIT

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot_size,
            "type": order,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "Telegram Trading Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        if tp is not None:
            request["tp"] = tp

        print(f"Placing order: {request}")
        result = mt5.order_send(request)
        if result is None:
            logger.error(f"order_send() failed, error code: {mt5.last_error()}")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed. Error code: {result.retcode}")
            logger.error(f"Error description: {mt5.last_error()}")
            return None

        logger.info(f"Order placed successfully. Order ticket: {result.order}")
        return result
    except Exception as e:
        logger.exception(f"Error placing order: {e}")
        return None

async def handle_signal(signal):
    try:
        symbol = signal['symbol']
        order_type = signal['type']
        entry_ranges = signal['entry_ranges']
        tp_levels = signal['tp_levels']
        sl = signal['sl']
        
        orders_per_range = NUM_ORDERS // len(tp_levels)
        
        for entry_range in entry_ranges:
            entry_start, entry_end = entry_range
            step = (entry_end - entry_start) / (orders_per_range - 1)
            
            for i in range(orders_per_range):
                entry_price = entry_start + i * step
                lot_size = calculate_lot_size(entry_price, sl, MAX_RISK_PER_TRADE, NUM_ORDERS)
                
                if lot_size is None:
                    logger.error("Failed to calculate lot size. Skipping order.")
                    continue
                
                for j, tp in enumerate(tp_levels):
                    order_number = i * len(tp_levels) + j + 1
                    result = place_order(symbol, lot_size, order_type, entry_price, sl, tp)
                    logger.info(f"Order {order_number} result: {result}")
                    await asyncio.sleep(1)  # Add a small delay between orders
    except Exception as e:
        logger.exception(f"Error handling signal: {e}")

async def check_telegram_signals():
    try:
        async with bot:
            async for message in bot.get_updates():
                if message.channel_post:
                    signal = parse_signal(message.channel_post.text)
                    if signal:
                        await handle_signal(signal)
    except Exception as e:
        logger.exception(f"Error checking Telegram signals: {e}")

def parse_signal(message_text):
    # Implement your signal parsing logic here
    # This should extract symbol, type, entry_ranges, tp_levels, and sl from the message
    # Return a dictionary with these values or None if the message is not a valid signal
    pass

async def place_orders_async(signal):
    try:
        await handle_signal(signal)
    except Exception as e:
        logger.exception(f"Error placing orders asynchronously: {e}")

def main():
    try:
        if not mt5.initialize():
            logger.error("Failed to initialize MT5. Exiting.")
            return

        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(place_orders_async(signal))
        finally:
            loop.close()
    except Exception as e:
        logger.exception(f"Error in main function: {e}")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
