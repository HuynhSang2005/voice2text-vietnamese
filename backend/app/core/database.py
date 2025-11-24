from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, text
from app.core.config import settings

sqlite_file_name = "database.db"
sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_async_engine(sqlite_url, echo=False, connect_args=connect_args)

async def create_db_and_tables():
    # Import models to ensure they are registered with SQLModel.metadata
    from app.models import schema
    print(f"Creating tables. Metadata tables: {SQLModel.metadata.tables.keys()}")
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        # Enable WAL mode
        await conn.execute(text("PRAGMA journal_mode=WAL;"))

async def get_session():
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
