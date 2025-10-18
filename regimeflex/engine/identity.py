from colorama import init as colorama_init, Fore, Style

colorama_init(autoreset=True)

class RegimeFlexIdentity:
    VERSION = "v1.0.0"
    BRAND_NAME = "RegimeFlex"
    BRAND_COLORS = {
        "primary": "#1a237e",
        "accent": "#00d4ff",
        "success": "#10b981",
        "danger": "#ef4444"
    }

    LEVEL_ICONS = {
        "INFO": "ℹ️",
        "SIGNAL": "🎯",
        "RISK": "⚡",
        "ERROR": "❌",
        "SUCCESS": "✅"
    }

    LEVEL_COLORS = {
        "INFO": Fore.CYAN,
        "SIGNAL": Fore.GREEN,
        "RISK": Fore.YELLOW,
        "ERROR": Fore.RED,
        "SUCCESS": Fore.GREEN,
    }

    @classmethod
    def formatted_log(cls, message, level="INFO"):
        icon = cls.LEVEL_ICONS.get(level, "📝")
        return f"{icon} {cls.BRAND_NAME} | {message}"

    @classmethod
    def print_log(cls, message, level="INFO"):
        color = cls.LEVEL_COLORS.get(level, Fore.WHITE)
        print(color + cls.formatted_log(message, level) + Style.RESET_ALL)



