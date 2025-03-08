import asyncio

import pandas as pd

from wanchain_api import WanchainAPIAsync


class StakingRewardsProcessor:
    def __init__(self, private_key, api_key, address, rows=25):
        self.private_key = private_key
        self.api_key = api_key
        self.address = address
        self.rows = rows
        self.staking_df = None
        self.wan_transactions = None
        self.wan_koinly = None

    async def query_multiple_epochs(self, epochs):
        api = WanchainAPIAsync(self.private_key, self.api_key)
        await api.connect()
        try:
            tasks = [
                api.run_query("getEpochIncentiveBlockNumber", epochID=epoch)
                for epoch in epochs
            ]
            results = await asyncio.gather(*tasks)
            return results
        finally:
            await api.close()

    async def query_multiple_block_numbers(self, block_numbers):
        api = WanchainAPIAsync(self.private_key, self.api_key)
        await api.connect()
        try:
            tasks = [
                api.run_query("getBlockByNumber", blockNumber=block_number)
                for block_number in block_numbers
            ]
            results = await asyncio.gather(*tasks)
            return results
        finally:
            await api.close()

    async def query_staking_pos(self):
        api = WanchainAPIAsync(self.private_key, self.api_key)
        await api.connect()
        try:
            result = await api.run_query("getDelegatorIncentive", address=self.address)
            return result
        finally:
            await api.close()

    async def add_block_numbers_to_df(self, df, epoch_col):
        if epoch_col not in df.columns:
            raise ValueError(f"Column '{epoch_col}' not found in the DataFrame.")

        epochs = df[epoch_col].tolist()
        results = await self.query_multiple_epochs(epochs)

        block_numbers = [
            result["result"] if result and "result" in result else None
            for result in results
        ]
        df["blockNumber"] = block_numbers

        return df

    async def add_timestamp_to_df(self, df, block_number_col):
        if block_number_col not in df.columns:
            raise ValueError(f"Column '{block_number_col}' not found in the DataFrame.")

        block_numbers = df[block_number_col].tolist()
        results = await self.query_multiple_block_numbers(block_numbers)

        timestamps = [
            result["result"]["timestamp"] if result and "result" in result else None
            for result in results
        ]
        df["timestamp"] = timestamps

        return df

    async def process_rewards(self):
        staking_res = await self.query_staking_pos()
        self.staking_df = pd.DataFrame(staking_res["result"])
        if self.rows:
            temp_df = self.staking_df.sort_values(by="epochId", ascending=False).head(
                int(self.rows)
            )
        else:
            temp_df = self.staking_df.sort_values(by="epochId", ascending=False)
        temp_df = await self.add_block_numbers_to_df(temp_df, "epochId")
        temp_df["amount"] = temp_df["amount"].astype(float) * 10**-18
        temp_df = await self.add_timestamp_to_df(temp_df, "blockNumber")
        temp_df["timestamp"] = pd.to_datetime(temp_df["timestamp"], unit="s", utc=True)

        self.wan_transactions = temp_df.copy()
        self.wan_transactions["Currency"] = "WAN"
        self.wan_transactions = self.wan_transactions[
            ["epochId", "blockNumber", "Currency", "amount", "timestamp"]
        ]
        self.wan_transactions.rename(
            columns={
                "epochId": "Epoch",
                "blockNumber": "Block",
                "amount": "Amount",
                "timestamp": "Date",
            },
            inplace=True,
        )
        self.wan_transactions.set_index("Epoch", inplace=True)
        self.wan_koinly = self.wan_transactions.copy()

        self.wan_koinly = self.wan_koinly.reset_index()[["Date", "Amount", "Currency"]]
        self.wan_koinly["label"] = "reward"
        self.wan_koinly.set_index("Date", inplace=True)
        self.wan_koinly.index.name = "Koinly Date"

    def get_wan_transactions(self):
        return self.wan_transactions

    def get_wan_koinly(self):
        return self.wan_koinly
