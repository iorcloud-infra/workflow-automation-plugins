from contextlib import asynccontextmanager
from ipaddress import IPv4Address

from cndi.annotations import Autowired
from cndi.events import EventHandler, Event
from cndi.initializers import AppInitializer
from fastapi import FastAPI
from langchain_elasticsearch import ElasticsearchStore
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel, Field
import socket, requests, ipaddress, os

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
    app_initializer = AppInitializer()
    app_initializer.run()

    yield

app = FastAPI(
    title="Workflow Runner Sentence Transformers",
    version="0.1.1",
    license_info={
        "name": "Apache 2.0",
        "identifier": "MIT",
    },
    lifespan=lifespan
)

class RetriverRequest(BaseModel):
    base_url: str = Field(description="Elasticsearch URL", default="http://localhost:9200")
    api_key: str
    index_name: str = Field(description="Elasticsearch index name", default="default")
    query: str = Field(description="Query to search for")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

@app.get("/name")
async def get_name():
    return dict(name=os.environ['JOB_NAME'])

@app.get("/retrieve")
async def root(request: RetriverRequest) -> dict:
    embeddings = HuggingFaceEmbeddings(model_name=request.embedding_model)
    retriever = ElasticsearchStore(es_url=request.base_url,
                                   index_name=request.index_name,
                                   embedding=embeddings,
                                   es_api_key=request.api_key
                                   )

    documents = await retriever.asearch(query = request.query)
    return dict(documents=documents)





def sync_ip(callEvent, eventObject):
    host_base_url = os.environ['HOST_SERVER_BASE_URL']
    port = int(os.environ.get("PORT"))
    requests.post(f"{host_base_url}/workers/{os.environ['JOB_ID']}/sync_ip", json={
        "hosts": get_all_ips(),
        "port": port
    }).json()

@Autowired()
def setEventHandler(event_handler: EventHandler):
    event = Event(event_name="testing_event",  # Event Name
                  event_handler=sync_ip,  # Set Handler Method
                  event_object=dict(informativeData="hello"),  # Set Initial EventData
                  event_invoker=lambda x: dict(trigger=True))

    event_handler.registerEvent(event)

