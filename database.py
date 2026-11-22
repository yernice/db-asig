import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("Set DATABASE_URL to your PostgreSQL connection URL.")

engine = create_engine(database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)
