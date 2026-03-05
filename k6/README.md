# k6 load tests

This directory contains k6 load-test scripts and utilities for the FastAPI API.

## Folder structure

```
k6/
├── README.md
├── k6_plotter.py          # Plot k6 JSON results (metrics + VUs)
├── k6_tests/              # k6 test scripts
│   ├── health-smoke.js
│   ├── health-db-smoke.js
│   └── heavy-get-cache-load.js
└── results/               # Optional: k6 JSON output (e.g. from --out json=...)
    ├── k6-result-redis.json
    └── k6-result-db.json
```

## Prerequisites

- API running locally, for example:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- k6 installed (see [k6 documentation](https://k6.io/docs/) for installation).

By default, health scripts target `http://localhost:8000`; the heavy GET script can target Render or any `BASE_URL`.

---

## Test scripts (`k6_tests/`)

### `heavy-get-cache-load.js`

Ramping load test for cached GET endpoints. Uses **stages**: ramps VUs up, holds at peak, then ramps down to 0.

**Endpoints exercised:**

- `GET /v2/users/orgs`
- `GET /v2/organizations/users?page=1&page_size=20`
- `GET /v2/projects?page=1&page_size=20`
- `GET /v2/projects/{project_id}/members`

**Run from project root (example with Render + JWT):**

```bash
BASE_URL=http://localhost:8000 \
JWT_TOKEN="<your_jwt_token>" \
PROJECT_ID=1 \
k6 run k6/k6_tests/heavy-get-cache-load.js
```

**Environment variables:**

| Env var     | Default / usage |
|------------|------------------|
| `BASE_URL` | `http://localhost:8000` |
| `JWT_TOKEN`| Access token for `Authorization: Bearer <token>` (required for protected endpoints). |
| `VUS`      | Peak VUs in stages (default `100`; stages use 100 → 150 → 200 → 250 → 500 then ramp down). |
| `PROJECT_ID` | Project ID for `GET /v2/projects/{project_id}/members`. Set in script or via env (e.g. `PROJECT_ID=123`). |

**Notes:**

- You can set `PROJECT_ID` in the script (e.g. `const PROJECT_ID = __ENV.PROJECT_ID || '1';`) or pass it when running.
- The script includes a commented **curl example** for manual testing with JWT; use the same token via `JWT_TOKEN`.
- Thresholds: p95 request duration &lt; 500 ms, checks rate &gt; 99%.

---

### `health-smoke.js`

Smoke test for `GET /health` (liveness).

**Run from project root:**

```bash
k6 run k6/k6_tests/health-smoke.js
```

| Env var    | Default              |
|-----------|----------------------|
| `BASE_URL`| `http://localhost:8000` |
| `VUS`     | `1000`               |
| `DURATION`| `10s`                |

---

### `health-db-smoke.js`

Smoke test for `GET /health/db` (DB readiness).

**Run from project root:**

```bash
k6 run k6/k6_tests/health-db-smoke.js
```

| Env var    | Default              |
|-----------|----------------------|
| `BASE_URL`| `http://localhost:8000` |
| `VUS`     | `1000`               |
| `DURATION`| `30s`                |

---

## Results and plotting

### Writing JSON results

To save k6 metrics for later analysis or plotting:

```bash
k6 run --out json=k6/results/my-test.json k6/k6_tests/heavy-get-cache-load.js
```

### `k6_plotter.py`

Plots a k6 JSON output file: average and max of a chosen metric over time, plus VU count.

**Usage from project root:**

```bash
# Plot default metric (http_req_waiting)
uv run k6/k6_plotter.py k6/results/k6-result-db.json

# Plot a specific metric
uv run k6/k6_plotter.py k6/results/k6-result-db.json http_req_duration
```

---

## Quick reference

| Script                  | Purpose                    | Typical use                    |
|-------------------------|----------------------------|--------------------------------|
| `k6_tests/health-smoke.js`      | Liveness `/health`         | Smoke / sanity                 |
| `k6_tests/health-db-smoke.js`  | DB health `/health/db`     | Smoke / sanity                 |
| `k6_tests/heavy-get-cache-load.js` | Cached GETs + project members | Ramping load vs Render/local   |
