"""
Module entrypoint for regimeflex.engine

Allows execution via: python -m regimeflex.engine.runner

This ensures proper package context so all relative imports work correctly.
"""

import sys

# Import and run the main function from runner module
from .runner import main

if __name__ == "__main__":
    sys.exit(main())

