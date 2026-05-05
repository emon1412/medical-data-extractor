FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install runtime deps from the root requirements.txt (kept slim for prod).
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt && pip install "uvicorn[standard]"

# Copy backend source
COPY backend/app /app/app

EXPOSE 8080
# Cloud Run injects $PORT (defaults to 8080).
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
