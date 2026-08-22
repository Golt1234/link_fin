import logging

logger = logging.getLogger('main.core.data_loader')

import polars as pl


from validators import AddressSchema, NameSchema
from .db_connector import get_adbc_connection


def get_accounts() -> pl.DataFrame:
    df_accounts = pl.scan_csv('./data/accounts.csv').collect()        
    return df_accounts

def get_daily_status() -> pl.DataFrame:
    """
    Collect all the daily date, ignores rows with null fields.
    """
    df_daily = (
        pl.scan_csv('./data/daily*.csv')
        .with_columns(
            pl.col("changed_datetime")
              .str.strptime(pl.Datetime, strict=False),
            pl.col("account").cast(pl.Int64, strict=False)
        )       
        .filter(pl.all_horizontal([pl.all().is_not_null()]))
        .collect()
    )
    return df_daily

def get_monthly_status() -> pl.DataFrame:
    """
    Collect all the monthly data, ignores rows with null fields.
    """
    df_monthly = (
        pl.scan_csv('./data/monthly*.csv')
        .with_columns(
            pl.col("account").cast(pl.Int64, strict=False)
            )        
        .filter(pl.all_horizontal([pl.all().is_not_null()]))
        .collect()
    )
    return df_monthly








