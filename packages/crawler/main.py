import asyncio
import os

from contextlib import asynccontextmanager
from uuid import UUID

from crawl4ai import BrowserConfig, AsyncWebCrawler
from crawl4ai.models import CrawlResultContainer
from sqlmodel import Session, select, desc

from app.models import SessionDep
from cndi.annotations import Autowired
from cndi.events import Event, EventHandler
from cndi.initializers import AppInitializer
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.db import getEngine
from app.models import CrawlTask

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_initializer = AppInitializer()
    app_initializer.run()
    yield



app = FastAPI(
    title="crawler",
    version="0.1.1",
    license_info={
        "name": "Apache 2.0",
        "identifier": "MIT",
    },
    lifespan=lifespan
)

class CrawlRequest(BaseModel):
    url: str = Field(description="URL to Crawl")

@app.get("/name")
async def get_name():
    return dict(name=os.environ['JOB_NAME'])

@app.post("/crawl")
async def crawl(request: CrawlRequest, session: SessionDep) -> dict:
    crawl_task = CrawlTask(url=request.url)
    session.add(crawl_task)
    session.commit()
    session.refresh(crawl_task)
    return dict(task_id=crawl_task.id)

@app.get("/task/{task_id}")
async def get_task(task_id: str, session: SessionDep):
    task = session.get(CrawlTask, UUID(task_id))
    return dict(task)



async def crawl_next():
    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
    )

    with (Session(getEngine()) as session):
        query = (select(CrawlTask).where(CrawlTask.status == "PENDING")
                        .order_by(desc(CrawlTask.priority))
                        .limit(1))
        for task in session.exec(query).all():
            task.status = "STARTED"
            session.merge(task)
            session.commit()

            try:
                async with AsyncWebCrawler(config=browser_config) as crawler:
                    result: CrawlResultContainer = await crawler.arun(
                        url=task.url,
                    )
                    task.result = result.markdown
                    task.status = "COMPLETED"

                session.merge(task)
            except Exception:
                task.status = "ERROR"
                session.merge(task)
            session.commit()


@Autowired()
def setEventHandler(event_handler: EventHandler):
    crawl_event = Event(event_name="crawl_event",  # Event Name
                  event_handler=lambda x,y: asyncio.run(crawl_next()),  # Set Handler Method
                  event_object=dict(informativeData="hello"),  # Set Initial EventData
                  event_invoker=lambda x: dict(trigger=True))

    event_handler.registerEvent(crawl_event)

