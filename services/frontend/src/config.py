from __future__ import annotations

import os


DOWNLOADER_BASE_URL = os.getenv("DOWNLOADER_BASE_URL", "http://localhost:8080", )

ANALYZER_BASE_URL = os.getenv("ANALYZER_BASE_URL", "http://localhost:8090", )

CHARTMGR_BASE_URL = os.getenv("CHARTMGR_BASE_URL", "http://localhost:8050", )

HOST = os.getenv("HOST", "0.0.0.0", )

PORT = int(os.getenv("PORT", "8000", ) )