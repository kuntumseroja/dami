import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.infrastructure.container import get_container


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema init is tolerant so the API can boot without a database for
    # rule-evaluation and workflow demos against the memory backend.
    with contextlib.suppress(Exception):
        await get_container().init()
    yield


app = FastAPI(
    title="DAM Governance Intelligence Platform",
    description="AI-assisted governance for Danantara DAM — drafting, consistency, routing, audit.",
    version="0.2.0",
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
