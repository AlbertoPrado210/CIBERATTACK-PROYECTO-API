import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import predictor
from routers import cyberattack

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servidor — precargando artefactos de ML ...")
    predictor._load_artifacts()
    logger.info("Artefactos listos. API operativa.")
    yield
    logger.info("Apagando servidor.")


app = FastAPI(
    title="CyberAttack Classifier API",
    description=(
        "API de clasificacion multiclase de ciberataques (28 categorias) "
        "usando XGBoost con tecnicas MITRE ATT&CK, herramientas, objetivo y fuente."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


app.include_router(cyberattack.router)


@app.get("/", tags=["Info"])
def index():
    return {
        "title":   "CyberAttack Classifier API v1.0",
        "message": "Consulta /docs para la documentacion interactiva.",
        "endpoints": {
            "health":              "GET  /health",
            "cyberattack_predict": "POST /cyberattack/predict",
            "cyberattack_classes": "GET  /cyberattack/classes",
        },
    }


@app.get("/health", tags=["Monitoring"], status_code=status.HTTP_200_OK)
def health_check():
    """Health check para monitoreo de Render."""
    try:
        art = predictor._load_artifacts()
    except Exception as exc:
        logger.error("Health check fallido: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Artefactos no disponibles: {str(exc)}",
        )
    return {
        "status":   "ok",
        "modelo":   type(art["model"]).__name__,
        "n_clases": len(art["le_target"].classes_),
        "features": art["feature_names"],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Excepcion no manejada en %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."},
    )
