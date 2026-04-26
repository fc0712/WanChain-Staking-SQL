import asyncio

import pandas as pd
from logger import logger

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
        self.api = None
        logger.info(f"Initialized StakingRewardsProcessor for address: {address}")

    async def connect(self):
        """Establish connection to Wanchain API"""
        logger.info("Establishing connection to Wanchain API")
        self.api = WanchainAPIAsync(self.private_key, self.api_key)
        await self.api.connect()
        logger.info("Successfully connected to Wanchain API")

    async def close(self):
        """Close connection to Wanchain API"""
        if self.api:
            await self.api.close()
            self.api = None
            logger.info("Closed connection to Wanchain API")

    async def query_multiple_epochs(self, epochs):
        logger.info(f"Querying multiple epochs: {len(epochs)} epochs to process")
        tasks = [
            self.api.run_query("getEpochIncentiveBlockNumber", epochID=epoch)
            for epoch in epochs
        ]
        results = await asyncio.gather(*tasks)
        logger.info(f"Successfully retrieved data for {len(results)} epochs")
        return results

    async def query_multiple_block_numbers(self, block_numbers):
        logger.info(
            f"Querying multiple block numbers: {len(block_numbers)} blocks to process"
        )
        tasks = [
            self.api.run_query("getBlockByNumber", blockNumber=block_number)
            for block_number in block_numbers
        ]
        results = await asyncio.gather(*tasks)
        logger.info(f"Successfully retrieved data for {len(results)} blocks")
        return results

    async def query_staking_pos(self):
        logger.info(f"Querying staking position for address: {self.address}")
        result = await self.api.run_query("getDelegatorIncentive", address=self.address)
        logger.info("Successfully retrieved staking position data")
        return result

    async def add_block_numbers_to_df(self, df, epoch_col):
        logger.info("Adding block numbers to DataFrame")
        if epoch_col not in df.columns:
            logger.error(f"Column '{epoch_col}' not found in the DataFrame")
            raise ValueError(f"Column '{epoch_col}' not found in the DataFrame.")

        epochs = df[epoch_col].tolist()
        results = await self.query_multiple_epochs(epochs)

        block_numbers = [
            result["result"] if result and "result" in result else None
            for result in results
        ]
        df["blockNumber"] = block_numbers
        logger.info("Successfully added block numbers to DataFrame")
        return df

    async def add_timestamp_to_df(self, df, block_number_col):
        logger.info("Adding timestamps to DataFrame")
        if block_number_col not in df.columns:
            logger.error(f"Column '{block_number_col}' not found in the DataFrame")
            raise ValueError(f"Column '{block_number_col}' not found in the DataFrame.")

        block_numbers = df[block_number_col].tolist()
        results = await self.query_multiple_block_numbers(block_numbers)

        timestamps = [
            result["result"]["timestamp"] if result and "result" in result else None
            for result in results
        ]
        df["timestamp"] = timestamps
        logger.info("Successfully added timestamps to DataFrame")
        return df

    async def process_rewards(self):
        """Main processing method"""
        try:
            await self.connect()
            logger.info("Starting rewards processing")

            staking_res = await self.query_staking_pos()
            self.staking_df = pd.DataFrame(staking_res["result"])
            logger.info(f"Retrieved {len(self.staking_df)} staking rewards records")

            sorted_df = self.staking_df.sort_values(by="epochId", ascending=False)
            temp_df = (sorted_df.head(int(self.rows)) if self.rows else sorted_df).copy()

            temp_df = await self.add_block_numbers_to_df(temp_df, "epochId")
            temp_df["amount"] = temp_df["amount"].astype(float) * 10**-18
            logger.info("Converted amounts to WAN")

            temp_df = await self.add_timestamp_to_df(temp_df, "blockNumber")
            temp_df["timestamp"] = pd.to_datetime(
                temp_df["timestamp"], unit="s", utc=True
            )
            logger.info("Converted timestamps to datetime")

            self.wan_transactions = (
                temp_df[["epochId", "blockNumber", "amount", "timestamp"]]
                .assign(Currency="WAN")
                .rename(columns={"epochId": "Epoch", "blockNumber": "Block", "amount": "Amount", "timestamp": "Date"})
                .set_index("Epoch")
            )
            logger.info("Created WAN transactions DataFrame")

            self.wan_koinly = (
                self.wan_transactions.reset_index()[["Date", "Amount", "Currency"]]
                .assign(label="reward")
                .set_index("Date")
                .rename_axis("Koinly Date")
            )
            logger.info("Created Koinly format DataFrame")

        finally:
            await self.close()

    def get_wan_transactions(self):
        logger.info("Returning WAN transactions DataFrame")
        return self.wan_transactions

    def get_wan_koinly(self):
        logger.info("Returning Koinly format DataFrame")
        return self.wan_koinly
