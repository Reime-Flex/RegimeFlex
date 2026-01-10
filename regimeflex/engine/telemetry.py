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

    def send_heartbeat(self, bc: dict):
        # minimal, single-line
        parts = []
        parts.append("💓 *RegimeFlex Heartbeat*")
        if bc.get("config_hash16"):
            parts.append(f"`{bc['config_hash16']}`")
        if bc.get("price_common_date"):
            parts.append(f"· {bc['price_common_date']}")
        pair = f"{bc.get('exec_long','')} / {bc.get('exec_short','')}"
        if pair.strip() and pair.strip() != " / ":
            parts.append(f"· {pair}")
        dur = bc.get("run_duration_sec")
        if dur is not None:
            try: 
                parts.append(f"· {float(dur):.2f}s")
            except: 
                pass
        if bc.get("no_op"):
            parts.append(f"· no-op: *{bc.get('no_op_reason','')}*")
        if bc.get("price_stale", False):
            parts.append("· ⚠️ stale prices")
        if bc.get("drift_warn", False):
            parts.append("· ⚠️ drift")
        
        # Priority 3: Add System Health to Heartbeat
        try:
            health = check_system_health()
            health_summary = format_health_summary(health)
            parts.append(f"· {health_summary}")
            bc["system_health"] = health  # Add to crumbs for logging
        except Exception as e:
            RF.print_log(f"System health check failed in heartbeat: {e}", "RISK")
        
        msg = " ".join(parts)
        self.send(msg)

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

        sess = bc.get("session","")
        if sess:
            brief.append(f"*Session*: {sess}")

        phase = bc.get("phase", "")
        if phase:
            brief.append(f"*Phase*: {phase}")

        # Exposure breadcrumbs (prev → desired with delta)
        prev = bc.get("prev_exposure", {})
        des  = bc.get("desired_exposure", {})
        dlt  = bc.get("delta_exposure", {})
        if prev and des and dlt:
            def fmt(x): 
                try: return f"{float(x)*100:.0f}%"
                except: return "0%"
            brief.append(
                f"*Exposure*  TQQQ: {fmt(prev.get('TQQQ',0))}→{fmt(des.get('TQQQ',0))} (Δ{fmt(dlt.get('TQQQ',0))}) · "
                f"SQQQ: {fmt(prev.get('SQQQ',0))}→{fmt(des.get('SQQQ',0))} (Δ{fmt(dlt.get('SQQQ',0))})"
            )

        reason = bc.get("plan_reason", "")
        if reason:
            brief.append(f"*Why*: {reason}")

        if bc.get("cash_mode", False):
            brief.append("*Target*: CASH (0% exposure)")

        tovf = bc.get("turnover_frac", None)
        tovn = bc.get("turnover_note", "")
        if tovf is not None:
            brief.append(f"*Turnover*: {float(tovf)*100:.0f}% — {tovn}")

        src = bc.get("positions_source", "")
        enow = bc.get("equity_now", None)
        if src:
            brief.append(f"*Positions*: {src}")
        if enow is not None:
            try:
                brief.append(f"*Equity (live)*: ${float(enow):,.0f}")
            except Exception:
                pass

        pcd = bc.get("price_common_date", "")
        if pcd:
            brief.append(f"*As-of*: {pcd}")

        # Config echo
        ce = bc.get("config_echo", {})
        if ce:
            brief.append(f"*CFG*: {ce.get('pair','')}, eod {ce.get('eod','')}, tov {ce.get('turnover','')}")

        stale = bc.get("price_stale", False)
        if stale:
            lag = bc.get("price_staleness_days", 0)
            brief.append(f"*Data stale*: {int(lag)}d old")

        if bc.get("sanity_violation", False):
            brief.append(f"*Sanity*: {bc.get('sanity_note','')}")

        if bc.get("drift_warn", False):
            brief.append("*Drift*: WARN (broker≠local)")
        elif bc.get("drift_note","") == "no_broker_snapshot":
            brief.append("*Drift*: n/a (no broker)")
        elif bc.get("drift_note","") == "OK":
            brief.append("*Drift*: OK")

        no_op = bc.get("no_op", False)
        if no_op:
            brief.append(f"*No-op*: {bc.get('no_op_reason','')}")

        if bc.get("env_forced_dry_run", False):
            brief.append("⚠️ *ENV GUARD*: forced dry_run")
        elif bc.get("dry_run", False):
            brief.append("_dry_run_")

        dur = bc.get("run_duration_sec", None)
        if dur is not None:
            try:
                brief.append(f"*Run*: {float(dur):.2f}s")
            except Exception:
                pass

        # TSI (Turnover Stability Index)
        avg = bc.get("tsi_avg_turnover", None)
        win = bc.get("tsi_window_days", 7)
        warn = bc.get("tsi_warn", False)
        if avg is not None:
            line = f"*TSI*: {float(avg)*100:.0f}% avg over {int(win)}d"
            if warn:
                line += " ⚠️"
            brief.append(line)

        # Report hash
        rh = bc.get("report_sha256", "")
        if rh:
            brief.append(f"*Report hash*: `{rh[:8]}…`")

        # Config hash
        if bc.get("config_hash16"):
            brief.append(f"`{bc['config_hash16']}`")

        # Bar hygiene
        if bc.get("bar_hygiene_fail", False):
            brief.append("*Bar hygiene*: FAIL")

        # Signal stability
        stab = bc.get("signal_stability", {})
        if stab and "note" not in stab:
            try:
                t = stab.get("trend", {})
                m = stab.get("mr", {})
                # Example: STAB T:0.86/2  MR:0.71/4  (score/flipcount)
                brief.append(f"*STAB* T:{t.get('score','-')}/{t.get('flips','-')} MR:{m.get('score','-')}/{m.get('flips','-')}")
            except Exception:
                pass

        # Execution quality
        eq = bc.get("exec_quality", {})
        if eq and eq.get("count",0) > 0 and eq.get("avg_bps") is not None:
            brief.append(f"*Slippage* {eq['avg_bps']}bps (p95 {eq['p95_bps']} / n={eq['count']})")

        # Exposure concentration
        xc = bc.get("exposure_concentration", {})
        if xc:
            net_pct = xc.get("net_abs", 0.0)
            net_badge = xc.get("net_badge", "")
            peak_sym = xc.get("peak_symbol", "")
            peak_pct = xc.get("peak_abs", 0.0)
            peak_badge = xc.get("peak_badge", "")
            conc_line = f"*Conc* net {net_pct:.0%} {net_badge}"
            if peak_sym:
                conc_line += f" · {peak_sym}: {peak_pct:.0%} {peak_badge}"
            brief.append(conc_line)

        # Liquidity depth
        liq = bc.get("liquidity_depth", {})
        if liq and liq.get("rows"):
            cts = liq.get("counts", {})
            brief.append(f"*Liquidity* G:{cts.get('GREEN',0)} A:{cts.get('AMBER',0)} R:{cts.get('RED',0)}")

        # Fill-quality drift
        fd = bc.get("fill_quality_drift", {})
        if fd and (fd.get("current_avg") is not None) and (fd.get("baseline_avg") is not None):
            s = f"*Drift* {fd['current_avg']} vs {fd['baseline_avg']} bps"
            if fd.get("alert"):
                s += f" (Δ {fd.get('delta_bps','?')} > {fd.get('threshold_bps','?')}) ⚠️"
            brief.append(s)

        # ADV guardrail
        ag = bc.get("adv_guardrail", {})
        if ag and ag.get("violations"):
            act = ag.get("action", "")
            brief.append(f"*ADV* {act} {len(ag['violations'])} viol")

        if verbosity == "full":
            brief.append(f"*Notes*: `{bc.get('target_notes','')}`")
            brief.append(f"*Positions After*: `{after}`")
        else:
            # brief mode: include positions only if changed
            if after:
                brief.append(f"*Pos After*: `{after}`")

        return "\n".join(hdr + brief)
