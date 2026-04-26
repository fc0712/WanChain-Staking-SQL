import asyncio
import base64
import hashlib
import hmac
import itertools
import json
import random
import time

import websockets

_RATE_LIMIT_MAX_RETRIES = 4


class _RateLimiter:
    """Token bucket: issues at most `rate` tokens per second."""

    def __init__(self, rate):
        self._rate = rate
        self._tokens = float(rate)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        while True:
            async with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    float(self._rate),
                    self._tokens + (now - self._last) * self._rate,
                )
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)


class WanchainAPIAsync:
    def __init__(
        self,
        private_key,
        api_key,
        wss_url="wss://api.wanchain.org:8443/ws/v3",
        rate_per_second=10,
    ):
        self.private_key = private_key
        self.api_key = api_key
        self.wss_url = f"{wss_url}/{api_key}"
        self.connection = None
        self._pending: dict[int, asyncio.Future] = {}
        self._id_counter = itertools.count(1)
        self._listener_task = None
        self._rate_limiter = _RateLimiter(rate_per_second)

    async def connect(self):
        self.connection = await websockets.connect(self.wss_url)
        self._listener_task = asyncio.create_task(self._listen())
        print("Connected to Wanchain via WSS")

    async def _listen(self):
        async for raw in self.connection:
            msg = json.loads(raw)
            fut = self._pending.pop(msg.get("id"), None)
            if fut and not fut.done():
                fut.set_result(msg)

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.connection:
            await self.connection.close()
            print("Connection closed")

    async def run_query(self, method, **params):
        if not self.connection:
            raise RuntimeError("Connection not established. Call 'connect()' first.")

        req_id = next(self._id_counter)

        for attempt in range(_RATE_LIMIT_MAX_RETRIES):
            await self._rate_limiter.acquire()

            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": {
                    **params,
                    "chainType": "WAN",
                    "timestamp": int(time.time() * 1000),
                },
                "id": req_id,
            }
            payload["params"]["signature"] = base64.b64encode(
                hmac.new(
                    self.private_key.encode("utf-8"),
                    json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                    hashlib.sha256,
                ).digest()
            ).decode("utf-8")

            fut = asyncio.get_running_loop().create_future()
            self._pending[req_id] = fut
            await self.connection.send(json.dumps(payload, separators=(",", ":")))
            response = await fut

            if "error" not in response:
                return response

            error = response["error"]
            if "rate limit" in str(error).lower() and attempt < _RATE_LIMIT_MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
                continue

            raise RuntimeError(f"Wanchain API error for '{method}': {error}")
