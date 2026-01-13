import asyncio
import os
import time
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
INSIGHTS_PATH = os.getenv("INSIGHTS_PATH", "/api/insights/today")

# If your endpoint needs auth, set TOKEN env var and we'll attach it.
TOKEN = os.getenv("TOKEN")  # "Bearer <jwt>" or "<jwt>" depending on your API

TOTAL = int(os.getenv("TOTAL", "300"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "25"))
TIMEOUT_S = float(os.getenv("TIMEOUT_S", "15"))

def auth_headers():
    if not TOKEN:
        return {}
    if TOKEN.lower().startswith("bearer "):
        return {"Authorization": TOKEN}
    return {"Authorization": f"Bearer {TOKEN}"}

async def one_request(client: httpx.AsyncClient):
    url = f"{BASE_URL}{INSIGHTS_PATH}"
    t0 = time.perf_counter()
    r = await client.get(url, headers=auth_headers(), timeout=TIMEOUT_S)
    dt_ms = (time.perf_counter() - t0) * 1000
    return r.status_code, dt_ms

async def main():
    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY, max_connections=CONCURRENCY)
    async with httpx.AsyncClient(limits=limits) as client:
        dts = []
        ok = 0
        for i in range(0, TOTAL, CONCURRENCY):
            batch = [one_request(client) for _ in range(min(CONCURRENCY, TOTAL - i))]
            results = await asyncio.gather(*batch, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    continue
                status, dt = res
                if status == 200:
                    ok += 1
                dts.append(dt)

        if not dts:
            print("No successful timings collected.")
            return

        dts.sort()
        p50 = dts[int(0.50 * len(dts)) - 1]
        p95 = dts[int(0.95 * len(dts)) - 1]
        p99 = dts[int(0.99 * len(dts)) - 1]
        print(f"OK {ok}/{TOTAL}")
        print(f"p50={p50:.1f}ms  p95={p95:.1f}ms  p99={p99:.1f}ms  max={max(dts):.1f}ms")

if __name__ == "__main__":
    asyncio.run(main())
