from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import agents, articles, properties


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="OpenClaw Real Estate API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://frontend:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(articles.router, prefix="/api/articles", tags=["articles"])
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok"}
