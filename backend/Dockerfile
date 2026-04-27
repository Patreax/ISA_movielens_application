# ISA MovieLens Recommendation API — single-stage image (Constitution III).
#
# Build context is `backend/` (see docker-compose.yaml at the repo root, or
# `cd backend && docker build -t isa-movielens-backend .`).
#
# Build deps for scikit-surprise (Cython, BLAS) are kept around for the demo;
# image size is well under any reasonable budget. Switch to multi-stage only
# if size becomes a problem.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Drop build deps after wheels are installed to keep the image lean.
RUN apt-get purge -y --auto-remove build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/*

COPY src    /app/src
COPY models /app/models
COPY data   /app/data

EXPOSE 8000

CMD ["uvicorn", "recsys_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
