import asyncio
import hashlib
import hmac
import itertools
import json
import time

import websockets


class WanchainAPIAsync:
    def __init__(
        self, private_key, api_key, wss_url="wss://api.wanchain.org:8443/ws/v3"
    ):
        self.private_key = private_key
        self.api_key = api_key
        self.wss_url = f"{wss_url}/{api_key}"
        self.connection = None
        self._pending: dict[int, asyncio.Future] = {}
        self._id_counter = itertools.count(1)
        self._listener_task = None

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

    def generate_signature(self, message):
        return hmac.new(
            bytes.fromhex(self.private_key), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    async def run_query(self, method, **params):
        if not self.connection:
            raise RuntimeError("Connection not established. Call 'connect()' first.")

        timestamp = int(time.time())
        signature = self.generate_signature(f"{method}{timestamp}")
        req_id = next(self._id_counter)

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                **params,
                "chainType": "WAN",
                "timestamp": str(timestamp),
                "signature": signature,
            },
            "id": req_id,
        }

        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self.connection.send(json.dumps(payload))
        return await fut
