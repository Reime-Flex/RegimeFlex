from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from .identity import RegimeFlexIdentity as RF

try:
    from telegram import Bot
except Exception:  # library not installed or env missing; we'll dry-run
    Bot = None  # type: ignore

@dataclass(frozen=True)
class TGCreds:
    token: Optional[str]
    chat_id: Optional[str]

class Notifier:
    def __init__(self, creds: TGCreds):
        self.creds = creds
        self._bot = Bot(creds.token) if (Bot and creds.token) else None
        self._dry = not (self._bot and self.creds.chat_id)

    async def _send_async(self, text: str):
        if self._dry:
            RF.print_log(f"[TELEGRAM DRY-RUN]\n{text}", "INFO")
            return
        try:
            assert self._bot is not None
            await self._bot.send_message(chat_id=self.creds.chat_id, text=text, parse_mode="Markdown")
            RF.print_log("Telegram message sent.", "SUCCESS")
        except Exception as e:
            RF.print_log(f"Telegram send failed: {e}", "ERROR")

    def send(self, text: str):
        # minimal sync wrapper
        try:
            asyncio.run(self._send_async(text))
        except RuntimeError:
            # already in an event loop (rare in our CLI); fallback
            RF.print_log("[TELEGRAM] event loop in use; falling back to dry-run", "RISK")
            RF.print_log(f"[TELEGRAM DRY-RUN]\n{text}", "INFO")

    @staticmethod
    def format_run_summary(result: Dict[str, Any], verbosity: str = "brief") -> str:
        t = result.get("target", {})
        dirn = t.get("direction", "FLAT")
        sym = t.get("symbol", "NA")
        notional = t.get("dollars", 0.0)
        shares = t.get("shares", 0.0)
        intents = result.get("intents", [])
        after = result.get("positions_after", {})
        bc = result.get("breadcrumbs", {}) or {}
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")

        hdr = [
            f"*🎯 RegimeFlex Daily Summary*  `{stamp}`",
            "━━━━━━━━━━━━━━━━━━━━",
            f"*Target*: {dirn} `{sym}`",
            f"*Notional*: ${notional:,.2f}   *Shares*: {shares:,.2f}",
            f"*Planned Orders*: {len(intents)}",
        ]

        brief = [
            f"*VIX*: {bc.get('vix','?')}",
            f"*FOMC* blackout: {bc.get('fomc_blackout', False)}   *OPEX*: {bc.get('opex', False)}",
        ]

        if verbosity == "full":
            brief.append(f"*Notes*: `{bc.get('target_notes','')}`")
            brief.append(f"*Positions After*: `{after}`")
        else:
            # brief mode: include positions only if changed
            if after:
                brief.append(f"*Pos After*: `{after}`")

        return "\n".join(hdr + brief)
