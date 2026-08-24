import logging
import logging.config
from pathlib import Path
import yaml
import polars as pl
import pandera.polars as pa
from pandera.errors import SchemaErrors
from importlib import resources
from adbc_driver_postgresql.dbapi import Connection

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

def load_sql(filename: str) -> str:
    """
    Retrieve an sql query from an .sql in resource package.
    """
    return resources.files("resources").joinpath(filename).read_text()

def validate_schema(df: pl.DataFrame, schema: type[pa.DataFrameModel]) -> pl.DataFrame:
    """Validate a DataFrame against a schema and return only the valid rows."""
    try:
        return schema.validate(df, lazy=True)
    except SchemaErrors as err:
        # Get the indices of the failing rows
        invalid_indices = err.failure_cases["index"].unique().to_list()
        
        print(f"Dropping {len(invalid_indices)} invalid rows from {schema.__name__}")
        print(err.failure_cases)          
        
        return df.filter(~pl.arange(0, df.height).is_in(invalid_indices))

def load_data(conn: Connection) -> None:
    """
    Loads the csv data into the Postgres dv.
    Skips for each table that is already in the database.
    """
    logger.info("Account procesing started")

    
    cursor = conn.cursor()
    table_names_query = load_sql("table_names.sql")
    cursor.execute(table_names_query)

    tables = cursor.fetchall()
    tables = [item[0] for item in tables]


    # Read accounts
    if 'Accounts' not in tables:
        df_accounts = dl.get_accounts()

        df_clean_accounts = validate_schema(df_accounts, NameSchema)
        df_clean_accounts = validate_schema(df_clean_accounts, AddressSchema)

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

def store_recent_accounts(conn: Connection) -> None:
    """
    Retrieves accounts with activity (queue or status change) on or after 2025-01-01
    and places them into a new table in the database.
    """
    cursor = conn.cursor()
    recent_accounts_query = load_sql("query_step3.sql")
    cursor.execute(recent_accounts_query)

    # Convert the query data into a polars dataframe
    recent_accounts_data = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    df_recent_accounts = pl.DataFrame(recent_accounts_data, schema=columns)

    logger.info('Writing recent accounts info to Postgres DB')
    df_recent_accounts.write_database(
        table_name="Recent_Accounts",
        connection=conn,
        engine="adbc",
        if_table_exists="append",
    )

    # Save recent accounts to csv for evaluation    
    output_path = Path("output/recent_accounts.csv")
    df_recent_accounts.write_csv(output_path)
    logger.info(f"Recent accounts CSV written to {output_path}")

def get_recent_changes(conn: Connection) -> None:
    """
    4.	Determine the most recent queue and/or status change 
    for accounts that as of Nov 27th 2025 are in queues “COLLECTIONS” or “LEGAL”
    """
    cursor = conn.cursor()
    recent_changes_query = load_sql("query_step5.sql")
    cursor.execute(recent_changes_query)

    # Convert the query data into a polars dataframe
    recent_changes_data = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    df_recent_changes = pl.DataFrame(recent_changes_data, schema=columns)

    # Save recent accounts to csv for evaluation    
    output_path = Path("output/recent_changes.csv")
    df_recent_changes.write_csv(output_path)
    logger.info(f"Recent changes CSV written to {output_path}")


def main():    

    conn = get_adbc_connection()    

    load_data(conn)
    store_recent_accounts(conn)
    get_recent_changes(conn)
    


if __name__ == '__main__':
    main()