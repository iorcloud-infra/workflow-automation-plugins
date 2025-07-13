from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends
from sqlmodel import SQLModel, Session, Field
import time
from app.db import getEngine


def get_session():
    engine = getEngine()
    with Session(engine) as session:
        yield session


metadata = SQLModel.metadata
SessionDep = Annotated[Session, Depends(get_session)]

class CrawlTask(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    url: str
    priority: int = Field(default=100)
    status: str = Field(default="PENDING")
    updated_epoch: int = Field(default_factory=time.time)
    result: str | None = Field(default=None)