from __future__ import annotations

import os

DOWNLOADER_BASE_URL = os.getenv("DOWNLOADER_BASE_URL", "http://localhost:8080", ).rstrip("/")
ANALYZER_BASE_URL = os.getenv("ANALYZER_BASE_URL", "http://localhost:8090", ).rstrip("/")

HOST = "0.0.0.0"

PORT = int(os.getenv("PORT", "8050"))

DEFAULT_PERIOD = os.getenv("DEFAULT_PERIOD", "10y", )

DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "1d", )