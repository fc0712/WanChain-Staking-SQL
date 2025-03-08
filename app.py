import asyncio

import pandas as pd
from logger import logger
from pangres import upsert
from sqlalchemy import create_engine, inspect

from helper import ConfigManager
from staking_rewards_processor import StakingRewardsProcessor
from wanchain_api import WanchainAPIAsync


class export_to_sql:
    def __init__(self, wan_tran, koinly_tran, con_str):
        self.engine = create_engine(con_str)
        self.wan_tran = wan_tran
        self.koinly_tran = koinly_tran

    def trans_sql(self, data):
        upsert(
            con=self.engine, df=data, table_name=self.wan_tran, if_row_exists="ignore"
        )

    def koinly_sql(self, data):
        upsert(
            con=self.engine,
            df=data,
            table_name=self.koinly_tran,
            if_row_exists="ignore",
        )

    def has_table(self, table_name):
        inspector = inspect(self.engine)
        return inspector.has_table(table_name)


# Load configuration
config_manager = ConfigManager()
(
    connection_string,
    transaction_table,
    koinly_table,
    wan_adr,
    rows,
    private_key,
    api_key,
) = config_manager.apply_config()

# Check if the transactions table exists
ALL_TRANSACTIONS = config_manager.transactions_check(
    connection_string, transaction_table
)


# Usage example
async def main():
    processor = StakingRewardsProcessor(private_key, api_key, wan_adr, rows)
    await processor.process_rewards()
    wan_transactions = processor.get_wan_transactions()
    logger.info("Successfully processed Wanchain data")
    wan_koinly = processor.get_wan_koinly()
    logger.info("Successfully processed Koinly data")
    logger.info("Exporting data to SQL.....")
    logger.info(wan_koinly.info())
    exporter = export_to_sql(transaction_table, koinly_table, connection_string)
    exporter.trans_sql(wan_transactions)
    exporter.koinly_sql(wan_koinly)
    logger.info("Successfully exported Wanchain data to SQL server")
    logger.info("Successfully exported Koinly data to SQL server")


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
