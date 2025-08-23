from sqlalchemy.ext.asyncio import create_async_engine
from config.settings import Config

class DatabaseConfig:
    def __init__(self, config: Config):
        self.db_host = config.DB_HOST
        self.db_port = config.DB_PORT
        self.db_name = config.DB_NAME
        self.db_user = config.DB_USER
        self.db_password = config.DB_PASSWORD

    def get_db_url(self):
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )