"""
Centralized API key access with name normalization.

This module provides a unified interface for accessing API keys, handling
the mapping between RegimeFlex's custom environment variable names and
official SDK naming conventions (e.g., Alpaca SDK expects APCA_API_KEY_ID).

Usage:
    from regimeflex.config.api_keys import APIKeys
    
    # Get keys (tries both naming conventions)
    key = APIKeys.alpaca_key_id()
    secret = APIKeys.alpaca_secret()
    
    # Setup Alpaca SDK environment variables
    APIKeys.setup_alpaca_env()
"""

import os
from typing import Optional

# Alpaca paper trading base URL (default)
ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_URL = "https://api.alpaca.markets"


class APIKeys:
    """
    Centralized API key access with name normalization.
    
    This class handles the mapping between RegimeFlex's custom environment
    variable names and official SDK naming conventions.
    """
    
    @staticmethod
    def alpaca_key_id() -> str:
        """
        Get Alpaca API key ID (tries both naming conventions).
        
        Checks in order:
        1. APCA_API_KEY_ID (Alpaca SDK official name)
        2. ALPACA_KEY (RegimeFlex custom name)
        
        Returns:
            API key string, or empty string if not found
        """
        return os.getenv('APCA_API_KEY_ID') or os.getenv('ALPACA_KEY') or ''
    
    @staticmethod
    def alpaca_secret() -> str:
        """
        Get Alpaca API secret (tries both naming conventions).
        
        Checks in order:
        1. APCA_API_SECRET_KEY (Alpaca SDK official name)
        2. ALPACA_SECRET (RegimeFlex custom name)
        
        Returns:
            API secret string, or empty string if not found
        """
        return os.getenv('APCA_API_SECRET_KEY') or os.getenv('ALPACA_SECRET') or ''
    
    @staticmethod
    def alpaca_base_url() -> str:
        """
        Get Alpaca API base URL (tries both naming conventions).
        
        Checks in order:
        1. APCA_API_BASE_URL (Alpaca SDK official name)
        2. ALPACA_BASE_URL (RegimeFlex custom name)
        3. Default: paper trading URL
        
        Returns:
            Base URL string, defaults to paper trading URL
        """
        return (
            os.getenv('APCA_API_BASE_URL') or 
            os.getenv('ALPACA_BASE_URL') or 
            ALPACA_PAPER_URL
        )
    
    @staticmethod
    def alpaca_live_key_id() -> str:
        """
        Get Alpaca Live API key ID.
        
        Returns:
            Live API key string, or empty string if not found
        """
        return os.getenv('ALPACA_LIVE_KEY') or ''
    
    @staticmethod
    def alpaca_live_secret() -> str:
        """
        Get Alpaca Live API secret.
        
        Returns:
            Live API secret string, or empty string if not found
        """
        return os.getenv('ALPACA_LIVE_SECRET') or ''
    
    @staticmethod
    def alpaca_live_base_url() -> str:
        """
        Get Alpaca Live API base URL.
        
        Returns:
            Live base URL string, defaults to live trading URL
        """
        return os.getenv('ALPACA_LIVE_BASE_URL') or ALPACA_LIVE_URL
    
    @staticmethod
    def polygon_key() -> str:
        """
        Get Polygon.io API key (tries both naming conventions).
        
        Checks in order:
        1. POLYGON_KEY (RegimeFlex custom name)
        2. POLYGON_API_KEY (alternative name)
        
        Returns:
            API key string, or empty string if not found
        """
        return os.getenv('POLYGON_KEY') or os.getenv('POLYGON_API_KEY') or ''
    
    @staticmethod
    def telegram_bot_token() -> str:
        """
        Get Telegram bot token.
        
        Returns:
            Bot token string, or empty string if not found
        """
        return os.getenv('TELEGRAM_BOT_TOKEN') or ''
    
    @staticmethod
    def telegram_chat_id() -> str:
        """
        Get Telegram chat ID.
        
        Returns:
            Chat ID string, or empty string if not found
        """
        return os.getenv('TELEGRAM_CHAT_ID') or ''
    
    @staticmethod
    def setup_alpaca_env(verbose: bool = False) -> None:
        """
        Ensure Alpaca SDK environment variables are set.
        
        Call this before initializing Alpaca API clients to ensure SDK can find credentials.
        
        This method sets the official Alpaca SDK environment variable names
        (APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL) if they
        are not already set, using values from RegimeFlex's custom names.
        
        This ensures compatibility with the Alpaca SDK which expects these
        specific environment variable names.
        
        Args:
            verbose: If True, prints a message indicating SDK environment variables are set
        
        Note: Only sets variables if they are not already present, to avoid
        overriding existing values.
        """
        # Set APCA_API_KEY_ID if not already set
        if not os.getenv('APCA_API_KEY_ID'):
            key = APIKeys.alpaca_key_id()
            if key:
                os.environ['APCA_API_KEY_ID'] = key
        
        # Set APCA_API_SECRET_KEY if not already set
        if not os.getenv('APCA_API_SECRET_KEY'):
            secret = APIKeys.alpaca_secret()
            if secret:
                os.environ['APCA_API_SECRET_KEY'] = secret
        
        # Set APCA_API_BASE_URL if not already set
        if not os.getenv('APCA_API_BASE_URL'):
            base_url = APIKeys.alpaca_base_url()
            if base_url:
                os.environ['APCA_API_BASE_URL'] = base_url
        
        if verbose:
            print("✓ Alpaca SDK environment variables are set (APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL)")
    
    @staticmethod
    def has_alpaca_credentials() -> bool:
        """
        Check if Alpaca credentials are available.
        
        Returns:
            True if both key and secret are present, False otherwise
        """
        return bool(APIKeys.alpaca_key_id() and APIKeys.alpaca_secret())
    
    @staticmethod
    def has_polygon_key() -> bool:
        """
        Check if Polygon API key is available.
        
        Returns:
            True if Polygon key is present, False otherwise
        """
        return bool(APIKeys.polygon_key())
    
    @staticmethod
    def has_telegram_credentials() -> bool:
        """
        Check if Telegram credentials are available.
        
        Returns:
            True if both bot token and chat ID are present, False otherwise
        """
        return bool(APIKeys.telegram_bot_token() and APIKeys.telegram_chat_id())

