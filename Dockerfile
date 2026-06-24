# ─────────────────────────────────────────────────────────────────────────────
# Imagen base: Python 3.11 slim (Debian Bookworm)
# Usa la variante slim para minimizar el tamaño de la imagen (~50MB base).
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Variables de entorno de Python ───────────────────────────────────────────
# PYTHONUNBUFFERED: logs visibles en tiempo real en Render
# PYTHONDONTWRITEBYTECODE: no genera archivos .pyc innecesarios
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Dependencias del sistema ──────────────────────────────────────────────────
# libgomp1: requerida por XGBoost para paralelismo con OpenMP.
# build-essential: compiladores C/C++ para paquetes con extensiones nativas.
# Se limpia el cache de apt en el mismo layer para reducir tamaño de imagen.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo dentro del contenedor ───────────────────────────────
WORKDIR /app

# ── Instalar dependencias Python ──────────────────────────────────────────────
# Se copia requirements.txt primero (antes del codigo fuente) para que Docker
# reutilice el layer cacheado cuando el codigo cambia pero las deps no.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copiar el codigo fuente y los artefactos del modelo ──────────────────────
COPY . .

# ── Puerto expuesto ───────────────────────────────────────────────────────────
# Render inyecta la variable $PORT en tiempo de ejecucion.
# EXPOSE es documentacion; el puerto real lo define el CMD.
EXPOSE 8000

# ── Comando de arranque ───────────────────────────────────────────────────────
# - host 0.0.0.0: necesario para que Render alcance el contenedor desde fuera.
# - port ${PORT:-8000}: usa el puerto que Render inyecta; 8000 como fallback local.
# - workers 1: un solo worker es suficiente para Render free tier (512MB RAM).
#   Con plan pago puedes subir a 2-4 workers o usar --workers=$(nproc).
# - timeout-keep-alive 75: recomendado para Render (su proxy usa 75s).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 75"]
