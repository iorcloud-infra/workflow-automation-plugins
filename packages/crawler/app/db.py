import os

from sqlmodel import SQLModel, create_engine

def getEngine():
    connection_url = os.environ.get("DB_CONNECTION_URL")
    engine = create_engine(
        connection_url,
        # isolation_level="REPEATABLE READ",
        isolation_level="AUTOCOMMIT"
    )

    engine.connect()

    return engine