from fastapi import FastAPI

app = FastAPI(
    title="Workflow Runner Sentence Transformers",
    license_info={
        "name": "Apache 2.0",
        "identifier": "MIT",
    },
)

@app.get("/")
async def root() -> dict:
    return {"message": "Hello World"}

