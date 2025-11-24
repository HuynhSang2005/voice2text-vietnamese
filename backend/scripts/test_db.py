import asyncio
from app.core.database import create_db_and_tables

async def main():
    print("Running create_db_and_tables...")
    await create_db_and_tables()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
