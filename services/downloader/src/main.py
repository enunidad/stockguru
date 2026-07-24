from aiohttp import web
import os

from src.api import create_app
from src.service import DownloaderService

from .config import HOST, PORT

def main() -> None:
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, )

if __name__ == "__main__":
    main()