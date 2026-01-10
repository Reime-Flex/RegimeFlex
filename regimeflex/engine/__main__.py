"""
Module entrypoint for regimeflex.engine

Allows execution via: python -m regimeflex.engine.runner

Uses absolute imports for location-independent execution.
"""

import sys

# Import and run the main function from runner module
from regimeflex.engine.runner import main

if __name__ == "__main__":
    sys.exit(main())

