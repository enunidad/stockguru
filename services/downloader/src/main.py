from aiohttp import web
import os

from .api import create_app

from .config import HOST, PORT

def main() -> None:
    app = create_app()
    web.run_app(app, host=HOST, port=PORT, )

if __name__ == "__main__":
    main()