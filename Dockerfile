# ── Stage 1: Build Next.js static export ─────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY frontend/ ./

# Empty string → calls go to the same origin (FastAPI) in production
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ── Stage 2: Python runtime serving everything ────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY api.py ./
COPY aeo_diagnostic.py ./

# Copy Next.js static export produced in stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

EXPOSE 8080

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
