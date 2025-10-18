from pathlib import Path

KILL_SWITCH_PATH = Path("config/kill_switch.flag")

def is_killed() -> bool:
    return KILL_SWITCH_PATH.exists()

def enable():
    KILL_SWITCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    KILL_SWITCH_PATH.touch(exist_ok=True)

def disable():
    if KILL_SWITCH_PATH.exists():
        KILL_SWITCH_PATH.unlink()
