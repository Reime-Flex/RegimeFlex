import sys
from pathlib import Path

# Add parent directory to path to import engine module
sys.path.append(str(Path(__file__).parent.parent))
from engine.identity import RegimeFlexIdentity as RF
from engine.env import load_env
import requests

def get_chat_id():
    """Get your Telegram chat ID by sending a message to the bot"""
    RF.print_log("Getting Telegram chat ID...", "INFO")
    RF.print_log("1. Go to @RegimeFlex_bot on Telegram", "INFO")
    RF.print_log("2. Send any message to the bot (like 'hello')", "INFO")
    RF.print_log("3. Press Enter here to check for updates...", "INFO")
    
    input("Press Enter after sending a message to the bot...")
    
    e = load_env()
    if not e.telegram_bot_token:
        RF.print_log("TELEGRAM_BOT_TOKEN not found in environment", "ERROR")
        return
    
    # Get updates from Telegram API
    url = f"https://api.telegram.org/bot{e.telegram_bot_token}/getUpdates"
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok') and data.get('result'):
            latest_message = data['result'][-1]
            chat_id = latest_message['message']['chat']['id']
            RF.print_log(f"Found chat ID: {chat_id}", "SUCCESS")
            RF.print_log(f"Add this to your .env file: TELEGRAM_CHAT_ID={chat_id}", "SUCCESS")
        else:
            RF.print_log("No messages found. Make sure you sent a message to @RegimeFlex_bot", "ERROR")
    except Exception as ex:
        RF.print_log(f"Error getting chat ID: {ex}", "ERROR")

if __name__ == "__main__":
    get_chat_id()
