from setuptools import setup, find_packages

setup(
    name="regimeflex",
    version="30.0.0",
    description="RegimeFlex Trading System - Systematic trading with regime detection",
    author="RegimeFlex Team",
    packages=find_packages(),
    install_requires=[
        "colorama>=0.4.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "python-telegram-bot>=20.0",
        "matplotlib>=3.5.0",
        "flask>=2.3.0",
    ],
    python_requires=">=3.12",
)
