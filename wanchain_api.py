import asyncio
import hashlib
import hmac
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
        self.lock = asyncio.Lock()  # Lock to serialize access to WebSocket

    async def connect(self):
        self.connection = await websockets.connect(self.wss_url)
        print("Connected to Wanchain via WSS")

    async def close(self):
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

        # Prepare the message
        timestamp = int(time.time())
        message = f"{method}{timestamp}"
        signature = self.generate_signature(message)

        # Build the request payload
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                **params,
                "chainType": "WAN",
                "timestamp": str(timestamp),
                "signature": signature,
            },
            "id": 1,
        }

        # Serialize WebSocket communication using the lock
        async with self.lock:
            await self.connection.send(json.dumps(payload))
            response = await self.connection.recv()
            return json.loads(response)
