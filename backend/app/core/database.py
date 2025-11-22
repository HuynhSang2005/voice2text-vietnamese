from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Enable WAL mode
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL;")

def get_session():
    with Session(engine) as session:
        yield session
