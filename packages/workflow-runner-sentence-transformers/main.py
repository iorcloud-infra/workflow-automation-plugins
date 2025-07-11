from fastapi import FastAPI
from langchain_elasticsearch import ElasticsearchStore
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel, Field

app = FastAPI(
    title="Workflow Runner Sentence Transformers",
    version="0.1.1",
    license_info={
        "name": "Apache 2.0",
        "identifier": "MIT",
    },
)

class RetriverRequest(BaseModel):
    base_url: str = Field(description="Elasticsearch URL", default="http://localhost:9200")
    api_key: str
    index_name: str = Field(description="Elasticsearch index name", default="default")
    query: str = Field(description="Query to search for")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

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