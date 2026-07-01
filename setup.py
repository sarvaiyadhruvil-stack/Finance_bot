"""
setup.py — allows ``pip install -e .`` for the trading_bot package and
registers the ``trade`` console-script entry-point.
"""

from setuptools import find_packages, setup

setup(
    name="binance-futures-trading-bot",
    version="1.0.0",
    description="A production-quality Binance Futures Testnet trading CLI bot.",
    author="Trading Bot",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "requests>=2.31.0",
        "urllib3>=2.0.0",
        "python-dotenv>=1.0.0",
        "python-binance>=1.0.17",
    ],
    entry_points={
        "console_scripts": [
            "trade=trading_bot.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)
