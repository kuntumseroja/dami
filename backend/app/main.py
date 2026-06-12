import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.rag.vectorstore import init_store


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Vector store is optional at boot so the API runs without a database
    # (e.g. routing-rule evaluation and workflow demos).
    with contextlib.suppress(Exception):
        await init_store()
    yield


app = FastAPI(
    title="DAM Governance Intelligence Platform",
    description="AI-assisted governance for Danantara DAM — drafting, consistency, routing, audit.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
