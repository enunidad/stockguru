"""
collection of configs that can change depending on where service is being run
"""

import os

DOWNLOADER_BASE_URL = os.getenv("DOWNLOADER_BASE_URL", "http://localhost:8080", )

HOST = "0.0.0.0"

PORT = int(os.getenv("PORT", "8080"))