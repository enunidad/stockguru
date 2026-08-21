from __future__ import annotations

import os


HOST = os.getenv("HOST", "0.0.0.0", )

PORT = int(os.getenv("PORT", "8060", ))

CONNECTED_SERVICES = {"downloader": "http://localhost:8080",
                        "analyzer": "http://localhost:8090",
                        }

DOWNLOADER_BASE_URL = os.getenv("GLOBAL_BASE_URL", CONNECTED_SERVICES["downloader"], )

ANALYZER_BASE_URL = os.getenv("GLOBAL_BASE_URL", CONNECTED_SERVICES["analyzer"], )

