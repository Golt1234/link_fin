import logging
import logging.config
from pathlib import Path
import yaml
import polars as pl
import pandera.polars as pa
from pandera.errors import SchemaErrors

# Load project logger before everything else
project_root = Path(__file__).resolve().parent
config_path = project_root/"logger_config.yaml"

if not config_path.exists():
    raise FileNotFoundError(f"Logging config not found: {config_path}")

with config_path.open("r") as f:
    config = yaml.safe_load(f)

logging.config.dictConfig(config)
logger = logging.getLogger("main")    

from core import data_loader as dl
from core import get_adbc_connection
from validators import NameSchema, AddressSchema



def validate_and_drop_invalid(df: pl.DataFrame, schema: type[pa.DataFrameModel]) -> pl.DataFrame:
    """Validate a DataFrame against a schema and return only the valid rows."""
    try:
        return schema.validate(df, lazy=True)
    except SchemaErrors as err:
        # Get the indices of the failing rows
        invalid_indices = err.failure_cases["index"].unique().to_list()
        
        print(f"Dropping {len(invalid_indices)} invalid rows from {schema.__name__}")
        print(err.failure_cases)          # optional: shows why they failed
        
        return df.filter(~pl.arange(0, df.height).is_in(invalid_indices))

def load_data() -> None:
    """
    Loads the csv data into the Postgres dv.
    Skips if the tables is already in the database.
    """
    logger.info("Account procesing started")

    conn = get_adbc_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    tables = cursor.fetchall()
    tables = [item[0] for item in tables]


    # Read accounts
    if 'Accounts' not in tables:
        df_accounts = dl.get_accounts()

        df_clean_accounts = validate_and_drop_invalid(df_accounts, NameSchema)
        df_clean_accounts = validate_and_drop_invalid(df_clean_accounts, AddressSchema)

        logger.info(f"Original Accounts rows : {df_accounts.height}")
        logger.info(f"Clean Accounts rows    : {df_clean_accounts.height}")

        logger.info('Pushing accounts info to Postgres DB')
        df_accounts.write_database(
            table_name="Accounts",
            connection=conn,
            engine="adbc",
            if_table_exists="append",
        )

    # Read daily_status
    if 'Daily_Status' not in tables:
        logger.info('Reading daily status data.')
        df_daily_status = dl.get_daily_status()
        logger.info(f"Loaded daily status. Found {df_daily_status.height} valid rows.")

        logger.info('Pushing daily status info to Postgres DB')
        df_daily_status.write_database(
            table_name="Daily_Status",
            connection=conn,
            engine="adbc",
            if_table_exists="append",
        )

    # Read monthly status
    if 'Monthly_Status' not in tables:
        logger.info('Reading monthly status data.')
        df_monthly_status = dl.get_monthly_status()
        logger.info(f"Loaded monthly status. Found {df_monthly_status.height} valid rows.")    

        logger.info('Pushing monthly status info to Postgres DB')
        df_monthly_status.write_database(
            table_name="Monthly_Status",
            connection=conn,
            engine="adbc",
            if_table_exists="append",
        )



def main():    
    load_data()
    


if __name__ == '__main__':
    main()