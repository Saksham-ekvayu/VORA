import asyncio
import os
import sys

# Ensure we can import from vora_shared
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vora_shared.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def drop_alembic():
    url = get_settings().resolved_database_url()
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    except Exception as e:  # noqa: BLE001
        print(f"Could not drop alembic_version: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(drop_alembic())
