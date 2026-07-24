import os

DOWNLOADER_BASE_URL = os.getenv("DOWNLOADER_BASE_URL", "http://localhost:8080", )

HOST = "0.0.0.0"

PORT = int(os.getenv("PORT", "8090"))