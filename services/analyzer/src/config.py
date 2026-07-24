from __future__ import annotations

import os

DOWNLOADER_BASE_URL = os.getenv("DOWNLOADER_BASE_URL", "http://localhost:8080", ).rstrip("/")

HOST = "0.0.0.0"

PORT = int(os.getenv("PORT", "8090"))

DEFAULT_PERIOD = os.getenv("DEFAULT_PERIOD", "10y", )

DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "1d", )

DEFAULT_TRADING_PERIODS = int(os.getenv("DEFAULT_TRADING_PERIODS", "252", ) )