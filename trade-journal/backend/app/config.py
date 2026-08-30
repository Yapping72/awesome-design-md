import os


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://journal:journal@localhost:5432/trade_journal"
    )
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


settings = Settings()
