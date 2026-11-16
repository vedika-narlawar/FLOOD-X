# Stage 1: build frontend
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: backend + pipeline + static frontend (single container)
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgdal-dev gdal-bin && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline ./pipeline
COPY backend ./backend
COPY configs ./configs
COPY scripts ./scripts
COPY --from=web /web/dist ./frontend/dist
ENV FLOODX_DATA_DIR=/data FLOODX_ARTIFACTS_DIR=/artifacts
VOLUME ["/data", "/artifacts"]
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
