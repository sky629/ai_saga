import asyncio
import os
import sys

# Create loop policy for context manager usage
# Force localhost for script execution
os.environ["POSTGRES_HOST"] = "localhost"

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text

from app.common.storage.postgres import postgres_storage
from app.game.infrastructure.persistence.models.game_models import (
    GameMessage,
    GameSession,
)


async def check_sessions():
    async with postgres_storage.get_domain_read_session() as db:
        print("\n--- Checking Game Sessions ---")
        result = await db.execute(
            select(GameSession).order_by(GameSession.started_at.desc())
        )
        sessions = result.scalars().all()

        for s in sessions:
            print(f"Session ID: {s.id}")
            print(f"  Character ID: {s.character_id}")
            print(f"  Status: {s.status}")
            print(f"  Turn: {s.turn_count}")
            print(f"  Started At: {s.started_at}")

            # Check messages count and image_url
            msg_result = await db.execute(
                select(GameMessage).where(GameMessage.session_id == s.id)
            )
            messages = msg_result.scalars().all()
            print(f"  Messages: {len(messages)}")

            images = [m.image_url for m in messages if m.image_url]
            print(f"  Images Saved: {len(images)}")
            if images:
                print(f"  Last Image URL: {images[-1]}")
            print("-" * 30)


if __name__ == "__main__":
    asyncio.run(check_sessions())
