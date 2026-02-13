import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import settings


async def reset_data():
    # Construct URL directly
    url = settings.postgres_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(url, echo=True)

    async with engine.begin() as conn:
        print("Truncating tables...")
        await conn.execute(
            text("TRUNCATE TABLE game_sessions, characters CASCADE")
        )
        print("Tables truncated.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_data())
