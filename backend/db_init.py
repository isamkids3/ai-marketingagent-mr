import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.database import Base

# Importing models is required to register them on Base.metadata
from app.models import User, ChatSession, ChatMessage

async def init_db():
    db_url = settings.DATABASE_URL
    print(f"Target Database URL: {db_url}")

    # Extract target database name and server root connection string
    try:
        # split at the last slash
        root_url, db_name = db_url.rsplit("/", 1)
        if "?" in db_name:
            db_name = db_name.split("?", 1)[0]
    except Exception as e:
        print(f"Error parsing database URL: {e}")
        root_url = "postgresql+asyncpg://postgres:postgres@localhost:5432"
        db_name = "millenium_radius"

    # Connect to the default 'postgres' database to check/create target database
    postgres_url = f"{root_url}/postgres"
    print(f"Connecting to database server root: {postgres_url}")
    
    root_engine = create_async_engine(
        postgres_url,
        isolation_level="AUTOCOMMIT"  # Needed for CREATE DATABASE
    )

    try:
        async with root_engine.connect() as conn:
            # Check if target database exists
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            exists = result.scalar()
            
            if not exists:
                print(f"Database '{db_name}' does not exist. Creating...")
                await conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"Database '{db_name}' created successfully.")
            else:
                print(f"Database '{db_name}' already exists.")
    except Exception as e:
        print(f"Warning: Could not check or create database server-side: {e}")
        print("Will attempt to connect and create tables directly on target URL...")
    finally:
        await root_engine.dispose()

    # Connect to the target database and build the tables
    print(f"Connecting to target database '{db_name}' to create tables...")
    target_engine = create_async_engine(db_url)
    
    try:
        async with target_engine.begin() as conn:
            # Create all registered tables
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing tables: {e}")
        raise
    finally:
        await target_engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
