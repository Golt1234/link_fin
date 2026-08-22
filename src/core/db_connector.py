import adbc_driver_postgresql.dbapi as adbc
from .app_settings import Settings
from urllib.parse import quote

settings = Settings()

def get_adbc_connection():
    encoded_password = quote(settings.database.password.get_secret_value(), safe="")
    return adbc.connect(
        f"postgresql://{settings.database.user}:{encoded_password}"
        f"@{settings.database.host}:{settings.database.port}/{settings.database.database}"
    )
