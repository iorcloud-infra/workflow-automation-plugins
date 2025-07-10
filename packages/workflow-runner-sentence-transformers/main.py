from fastapi import FastAPI

app = FastAPI(
    title="Workflow Runner Sentence Transformers",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

@app.get("/")
async def root() -> dict:
    return {"message": "Hello World"}

