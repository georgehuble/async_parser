from pathlib import Path

from pydantic_settings import BaseSettings


class Postgres(BaseSettings):
    user: str
    password: str
    name: str
    host: str = "localhost"
    port: int = 5432

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "prefix": "db_"
    }


settings = Postgres()
