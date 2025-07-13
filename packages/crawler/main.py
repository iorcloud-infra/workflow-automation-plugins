import asyncio
import ipaddress
import os
import socket
from contextlib import asynccontextmanager
from ipaddress import IPv4Address
from uuid import UUID

import requests
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


def get_all_ips():
    ips = []
    hostname = socket.gethostname()
    for addr in socket.getaddrinfo(hostname, None):
        ip = ipaddress.ip_address(addr[4][0])
        if isinstance(ip, IPv4Address):
            ips.append(addr[4][0])
    return list(set(ips))

@asynccontextmanager
async def lifespan(app: FastAPI):


    yield

app = FastAPI(
    title="Crawl4AI",
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_initializer = AppInitializer()
    app_initializer.run()
    yield



def sync_ip(callEvent, eventObject):
    port = int(os.environ.get("PORT"))
    host_base_url = os.environ['HOST_SERVER_BASE_URL']
    requests.post(f"{host_base_url}/workers/{os.environ['JOB_ID']}/sync_ip", json={
        "hosts": get_all_ips(),
        "port": port
    }).json()


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
    sync_event = Event(event_name="sync_event",  # Event Name
                  event_handler=sync_ip,  # Set Handler Method
                  event_object=dict(informativeData="hello"),  # Set Initial EventData
                  event_invoker=lambda x: dict(trigger=True))

    crawl_event = Event(event_name="crawl_event",  # Event Name
                  event_handler=lambda x,y: asyncio.run(crawl_next()),  # Set Handler Method
                  event_object=dict(informativeData="hello"),  # Set Initial EventData
                  event_invoker=lambda x: dict(trigger=True))

    event_handler.registerEvent(sync_event)
    event_handler.registerEvent(crawl_event)

