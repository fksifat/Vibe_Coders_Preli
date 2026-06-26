import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # Must be before any module reads env vars

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routes import router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("QueueStorm Investigator starting up...")
    yield
    logger.info("QueueStorm Investigator shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="QueueStorm Ticket Investigator",
    description=(
        "AI-powered CRM ticket investigator for digital finance support. "
        "Analyzes customer complaints + transaction history to classify, route, "
        "and draft safe replies using Gemini with rule-based fallback."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
    logger.info("%s %s → %.3fs", request.method, request.url.path, elapsed)
    return response


# ── Validation error handler (422) ─────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request body. Please check the required fields and types."},
    )


# ── Global error handler (500) ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ── Include routes ─────────────────────────────────────────────────────────────
app.include_router(router)
