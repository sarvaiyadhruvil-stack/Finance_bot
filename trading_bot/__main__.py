"""
Allow the package to be run as a module: ``python -m trading_bot``
"""

import sys

from trading_bot.cli import main

if __name__ == "__main__":
    sys.exit(main())
