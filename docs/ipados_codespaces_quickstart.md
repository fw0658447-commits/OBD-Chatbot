# iPadOS / GitHub Codespaces Quickstart

This version is prepared for running the Trading Cockpit from an iPad. The iPad is only the browser/client; the app runs inside GitHub Codespaces.

## 1. Create a private GitHub repository

Create a new private repository, for example:

```text
trading-cockpit
```

Upload the project files or unzip this package inside the repository.

## 2. Open Codespaces

In GitHub:

```text
Code -> Codespaces -> Create codespace on main
```

Codespaces will read `.devcontainer/devcontainer.json` and prepare Python, Node.js and Docker.

## 3. Start the app

Open the terminal in Codespaces and run:

```bash
bash scripts/codespaces_start.sh
```

This starts:

- PostgreSQL
- Redis
- FastAPI backend on port 8000
- Next.js frontend on port 3000
- Paper-bot worker

## 4. Open the forwarded ports

In the Codespaces **Ports** tab:

- Open port `3000` for the Trading Cockpit frontend
- Open port `8000` for the backend API
- Add `/docs` to the port 8000 URL for the API documentation

## 5. Check status

```bash
bash scripts/codespaces_status.sh
```

Or run a full smoke test:

```bash
bash scripts/codespaces_smoke_test.sh
```

## 6. Use mock data first

The default configuration uses mock market data. Keep it this way until the frontend, backend, monitoring and paper-bot work correctly.

## 7. Activate real market data later

Edit `.env` or `docker-compose.yml` and set:

```text
MARKET_DATA_PROVIDER=twelve_data
MARKET_DATA_API_KEY=your_api_key
```

Restart:

```bash
bash scripts/codespaces_stop.sh
bash scripts/codespaces_start.sh
```

## 8. Important safety status

This version is still paper-trading only. Live trading is hard-locked and no real broker orders are sent.

## Troubleshooting

### Frontend opens but shows no data

Open backend `/docs` on port 8000 and verify the backend is running. In Codespaces, the frontend automatically infers the backend URL by replacing `-3000.app.github.dev` with `-8000.app.github.dev`.

### Docker Compose fails

Run:

```bash
docker ps
bash scripts/codespaces_logs.sh backend
```

### Reset everything

```bash
docker compose down -v
bash scripts/codespaces_start.sh
```
