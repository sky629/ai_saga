
import asyncio
from sqlalchemy import text
from app.common.storage.postgres import postgres_storage

async def reset_data():
    async with postgres_storage.get_domain_write_session() as db:
        print("Clearing game_sessions...")
        await db.execute(text("TRUNCATE TABLE game_sessions CASCADE"))
        print("Clearing characters...")
        await db.execute(text("TRUNCATE TABLE characters CASCADE"))
        await db.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(reset_data())
