from setuptools import setup, find_packages

# Read requirements from requirements.txt if it exists
try:
    with open("requirements.txt", "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    # Fallback to minimal requirements
    requirements = [
        "colorama>=0.4.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "pandas-market-calendars>=4.4.0",
        "python-telegram-bot>=20.0",
        "matplotlib>=3.5.0",
        "flask>=2.3.0",
        "numpy>=1.20.0",
        "psutil>=5.9.0",
        "pytest>=7.0",
    ]

setup(
    name="regimeflex",
    version="30.0.0",
    description="RegimeFlex Trading System - Systematic trading with regime detection",
    author="RegimeFlex Team",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.12",
    entry_points={
        "console_scripts": [
            "regimeflex-run=regimeflex.engine.runner:main",
            "regimeflex-http=regimeflex.scripts.run_http_trigger:main",
        ],
    },
)
