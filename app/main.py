"""FastAPI entry point (owner: Core app)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import get_engine
from app.models import Base
from app.routers import anonymized, auth, students, users, materials


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create the SQLite tables if they don't exist yet.
    Base.metadata.create_all(get_engine())
    if get_settings().seed_demo_users:
        from app.seed import seed
        seed()
    yield


app = FastAPI(title="Secure University Records", version="0.1.0", lifespan=lifespan)

# TODO(auth): SlowApi rate limiting
#   from slowapi import Limiter; from slowapi.util import get_remote_address
#   limiter = Limiter(key_func=get_remote_address); app.state.limiter = limiter
#   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(students.router)
app.include_router(anonymized.router)
app.include_router(materials.router)

@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
