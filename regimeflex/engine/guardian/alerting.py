"""
Guardian Alerting Module
========================
Multi-channel webhook integration for Discord and Telegram with priority-based routing.

Supports:
- Discord webhooks
- Telegram bot (extends existing telemetry)
- Scheduled heartbeat messages
- Emergency escalation
"""
from __future__ import annotations

import os
import asyncio
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..identity import RegimeFlexIdentity as RF
from ..config import Config

try:
    from telegram import Bot
except ImportError:
    Bot = None  # type: ignore


class AlertLevel(Enum):
    """Alert severity levels for routing decisions."""
    INFO = "info"
    WARNING = "warning"
    EMERGENCY = "emergency"


@dataclass
class AlertConfig:
    """Parsed alerting configuration."""
    discord_enabled: bool
    discord_webhook_url: Optional[str]
    telegram_enabled: bool
    telegram_token: Optional[str]
    telegram_chat_id: Optional[str]
    routing: Dict[str, List[str]]


class AlertManager:
    """
    Unified alerting system for RegimeFlex Guardian.
    
    Handles multi-channel alerts with priority-based routing:
    - INFO: routine status updates
    - WARNING: potential issues requiring attention
    - EMERGENCY: critical failures requiring immediate action
    """
    
    def __init__(self, root: Path | str = "."):
        self.root = Path(root) if isinstance(root, str) else root
        self._config = self._load_config()
        self._telegram_bot = self._init_telegram()
        self._start_time = datetime.now(timezone.utc)
        self._last_heartbeat: Optional[datetime] = None
    
    def _load_config(self) -> AlertConfig:
        """Load alerting configuration from guardian.yaml."""
        try:
            cfg = Config(self.root)
            guardian = cfg._load_yaml("config/guardian.yaml") or {}
            alerting = guardian.get("alerting", {})
            
            discord = alerting.get("discord", {})
            telegram = alerting.get("telegram", {})
            routing = alerting.get("routing", {
                "info": ["telegram"],
                "warning": ["telegram", "discord"],
                "emergency": ["telegram", "discord"]
            })
            
            # Get webhook URL from environment
            discord_webhook_env = discord.get("webhook_url_env", "DISCORD_WEBHOOK_URL")
            discord_webhook = os.environ.get(discord_webhook_env)
            
            # Get Telegram credentials from environment
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            
            return AlertConfig(
                discord_enabled=discord.get("enabled", False) and bool(discord_webhook),
                discord_webhook_url=discord_webhook,
                telegram_enabled=telegram.get("enabled", True) and bool(telegram_token and telegram_chat_id),
                telegram_token=telegram_token,
                telegram_chat_id=telegram_chat_id,
                routing=routing
            )
        except Exception as e:
            RF.print_log(f"Failed to load Guardian alerting config: {e}", "WARNING")
            return AlertConfig(
                discord_enabled=False,
                discord_webhook_url=None,
                telegram_enabled=False,
                telegram_token=None,
                telegram_chat_id=None,
                routing={"info": [], "warning": [], "emergency": []}
            )
    
    def _init_telegram(self) -> Optional[Any]:
        """Initialize Telegram bot if configured."""
        if Bot and self._config.telegram_enabled and self._config.telegram_token:
            try:
                return Bot(self._config.telegram_token)
            except Exception as e:
                RF.print_log(f"Failed to initialize Telegram bot: {e}", "WARNING")
        return None
    
    def _get_channels(self, level: AlertLevel) -> List[str]:
        """Get channels for a given alert level."""
        return self._config.routing.get(level.value, [])
    
    async def _send_telegram_async(self, text: str) -> bool:
        """Send message via Telegram (async)."""
        if not self._telegram_bot or not self._config.telegram_chat_id:
            RF.print_log(f"[TELEGRAM DRY-RUN]\n{text}", "INFO")
            return True
        
        try:
            await self._telegram_bot.send_message(
                chat_id=self._config.telegram_chat_id,
                text=text,
                parse_mode="Markdown"
            )
            RF.print_log("Telegram alert sent.", "SUCCESS")
            return True
        except Exception as e:
            RF.print_log(f"Telegram send failed: {e}", "ERROR")
            return False
    
    def _send_telegram(self, text: str) -> bool:
        """Send message via Telegram (sync wrapper)."""
        try:
            return asyncio.run(self._send_telegram_async(text))
        except RuntimeError:
            # Already in event loop
            RF.print_log(f"[TELEGRAM DRY-RUN]\n{text}", "INFO")
            return True
    
    def _send_discord(self, text: str, level: AlertLevel) -> bool:
        """Send message via Discord webhook."""
        if not self._config.discord_enabled or not self._config.discord_webhook_url:
            RF.print_log(f"[DISCORD DRY-RUN]\n{text}", "INFO")
            return True
        
        # Discord embed colors by severity
        colors = {
            AlertLevel.INFO: 0x3498db,      # Blue
            AlertLevel.WARNING: 0xf39c12,   # Orange
            AlertLevel.EMERGENCY: 0xe74c3c  # Red
        }
        
        # Discord embed icons
        icons = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.EMERGENCY: "🚨"
        }
        
        payload = {
            "embeds": [{
                "title": f"{icons[level]} RegimeFlex {level.value.upper()}",
                "description": text,
                "color": colors[level],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "RegimeFlex Guardian"}
            }]
        }
        
        try:
            r = requests.post(
                self._config.discord_webhook_url,
                json=payload,
                timeout=10
            )
            if r.status_code >= 400:
                RF.print_log(f"Discord webhook failed: {r.status_code} {r.text}", "ERROR")
                return False
            RF.print_log("Discord alert sent.", "SUCCESS")
            return True
        except Exception as e:
            RF.print_log(f"Discord send failed: {e}", "ERROR")
            return False
    
    def send(self, message: str, level: AlertLevel = AlertLevel.INFO) -> bool:
        """
        Send an alert to all configured channels for the given level.
        
        Args:
            message: The alert message
            level: Alert severity level
            
        Returns:
            True if at least one channel succeeded
        """
        channels = self._get_channels(level)
        success = False
        
        for channel in channels:
            if channel == "telegram":
                success = self._send_telegram(message) or success
            elif channel == "discord":
                success = self._send_discord(message, level) or success
        
        if not channels:
            # No channels configured, log locally
            RF.print_log(f"[ALERT {level.value.upper()}] {message}", "INFO")
            success = True
        
        return success
    
    def send_heartbeat(
        self,
        regime: str = "UNKNOWN",
        equity: float = 0.0,
        last_cycle: Optional[datetime] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a scheduled heartbeat message.
        
        Args:
            regime: Current market regime (BULL/BEAR/NEUTRAL)
            equity: Current account equity
            last_cycle: Timestamp of last successful trading cycle
            additional_info: Extra info to include
            
        Returns:
            True if heartbeat was sent successfully
        """
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - self._start_time).total_seconds()
        uptime_hours = uptime_seconds / 3600
        
        # Emoji based on regime
        regime_emoji = {
            "BULL": "🐂",
            "BEAR": "🐻",
            "NEUTRAL": "⚖️",
            "CASH": "💵"
        }.get(regime.upper(), "❓")
        
        parts = [
            f"💓 *RegimeFlex Heartbeat*",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"{regime_emoji} *Regime*: {regime}",
            f"💰 *Equity*: ${equity:,.2f}",
            f"⏱️ *Uptime*: {uptime_hours:.1f}h",
        ]
        
        if last_cycle:
            cycle_age = (now - last_cycle).total_seconds() / 60
            parts.append(f"🔄 *Last Cycle*: {cycle_age:.0f}m ago")
        
        if additional_info:
            for key, value in additional_info.items():
                parts.append(f"• *{key}*: {value}")
        
        parts.append(f"📅 {now.strftime('%Y-%m-%d %H:%M UTC')}")
        
        message = "\n".join(parts)
        self._last_heartbeat = now
        
        return self.send(message, AlertLevel.INFO)
    
    def send_emergency(
        self,
        error_type: str,
        error_message: str,
        trace: Optional[str] = None,
        service: Optional[str] = None
    ) -> bool:
        """
        Send an emergency alert for critical failures.
        
        Includes phone/SMS notification if configured.
        
        Args:
            error_type: Type of error (e.g., "API_FAILURE", "CIRCUIT_OPEN")
            error_message: Brief error description
            trace: Optional stack trace or detailed error info
            service: Optional service name that failed
            
        Returns:
            True if alert was sent successfully
        """
        parts = [
            f"🚨 *EMERGENCY - RegimeFlex*",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"*Error*: {error_type}",
        ]
        
        if service:
            parts.append(f"*Service*: {service}")
        
        parts.append(f"*Message*: {error_message}")
        
        if trace:
            # Truncate trace if too long
            max_trace = 500
            if len(trace) > max_trace:
                trace = trace[:max_trace] + "..."
            parts.append(f"\n```\n{trace}\n```")
        
        parts.append(f"\n📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        parts.append(f"⚡ *Immediate attention required*")
        
        message = "\n".join(parts)
        
        # Send to configured channels
        success = self.send(message, AlertLevel.EMERGENCY)
        
        # Also send phone/SMS emergency if configured
        self._send_phone_emergency(error_type, error_message, service)
        
        return success
    
    def _send_phone_emergency(
        self,
        error_type: str,
        error_message: str,
        service: Optional[str] = None
    ) -> bool:
        """
        Send emergency alert via phone/SMS (Twilio or similar).
        
        Args:
            error_type: Type of error
            error_message: Brief error description
            service: Optional service name
            
        Returns:
            True if sent successfully
        """
        try:
            cfg = Config(self.root)
            guardian = cfg._load_yaml("config/guardian.yaml") or {}
            emergency_cfg = guardian.get("emergency", {})
            
            if not emergency_cfg.get("enabled", False):
                return False
            
            phone_env = emergency_cfg.get("phone_env", "GUARDIAN_EMERGENCY_PHONE")
            phone_number = os.environ.get(phone_env)
            
            if not phone_number:
                RF.print_log("Emergency phone number not configured", "WARNING")
                return False
            
            # Try Twilio first
            twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
            twilio_from = os.environ.get("TWILIO_FROM_NUMBER")
            
            if twilio_sid and twilio_token and twilio_from:
                try:
                    from twilio.rest import Client
                    client = Client(twilio_sid, twilio_token)
                    
                    sms_body = f"🚨 RegimeFlex EMERGENCY\n{error_type}\n{error_message}"
                    if service:
                        sms_body += f"\nService: {service}"
                    
                    message = client.messages.create(
                        body=sms_body,
                        from_=twilio_from,
                        to=phone_number
                    )
                    RF.print_log(f"Emergency SMS sent to {phone_number}: {message.sid}", "SUCCESS")
                    return True
                except ImportError:
                    RF.print_log("Twilio not installed, skipping SMS", "WARNING")
                except Exception as e:
                    RF.print_log(f"Twilio SMS failed: {e}", "ERROR")
            
            # Fallback: Try generic webhook (for services like IFTTT, Zapier, etc.)
            webhook_url = os.environ.get("GUARDIAN_EMERGENCY_WEBHOOK")
            if webhook_url:
                try:
                    payload = {
                        "error_type": error_type,
                        "error_message": error_message,
                        "service": service,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "phone": phone_number
                    }
                    r = requests.post(webhook_url, json=payload, timeout=10)
                    if r.status_code < 400:
                        RF.print_log(f"Emergency webhook sent to {phone_number}", "SUCCESS")
                        return True
                except Exception as e:
                    RF.print_log(f"Emergency webhook failed: {e}", "ERROR")
            
            return False
            
        except Exception as e:
            RF.print_log(f"Phone emergency alert failed: {e}", "ERROR")
            return False
    
    def send_warning(self, title: str, message: str) -> bool:
        """
        Send a warning alert.
        
        Args:
            title: Warning title
            message: Warning details
            
        Returns:
            True if alert was sent successfully
        """
        text = f"⚠️ *{title}*\n\n{message}\n\n📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        return self.send(text, AlertLevel.WARNING)
    
    def get_uptime_hours(self) -> float:
        """Get process uptime in hours."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds() / 3600
    
    def get_last_heartbeat(self) -> Optional[datetime]:
        """Get timestamp of last heartbeat."""
        return self._last_heartbeat


# Singleton instance for convenience
_default_manager: Optional[AlertManager] = None


def get_alert_manager(root: Path | str = ".") -> AlertManager:
    """Get or create the default AlertManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AlertManager(root)
    return _default_manager
