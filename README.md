# StockGuru

Run the five services from the project root with Docker Compose:

```bash
docker compose up --build --wait
```

Open <http://localhost:8000>. Each service image installs its own `requirements.txt`, so the stack runs without a host Python virtual environment. The downloader cache lives in a Docker volume.

To test one service in its own image, replace `downloader` with the service name:

```bash
make downloader test
```

Run `make integration-test` to test the five services together in a temporary Docker stack. Tests that fetch live market data require access to Yahoo Finance.

After changing a service's dependencies, rebuild that service with `docker compose up -d --build downloader`. Stop the stack with `docker compose down`.
