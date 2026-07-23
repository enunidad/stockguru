from __future__ import annotations

import os


ANALYZER_HOST = os.getenv(
    "ANALYZER_HOST",
    "0.0.0.0",
)

ANALYZER_PORT = int(
    os.getenv(
        "ANALYZER_PORT",
        "8090",
    )
)

DOWNLOADER_BASE_URL = os.getenv(
    "DOWNLOADER_BASE_URL",
    "http://localhost:8080",
).rstrip("/")

DEFAULT_PERIOD = os.getenv(
    "DEFAULT_PERIOD",
    "10y",
)

DEFAULT_INTERVAL = os.getenv(
    "DEFAULT_INTERVAL",
    "1d",
)

DEFAULT_TRADING_PERIODS = int(
    os.getenv(
        "DEFAULT_TRADING_PERIODS",
        "252",
    )
)