# Build from repository root: docker build -f backend/Dockerfile -t field-shift-backend .
FROM python:3.12-slim
WORKDIR /srv/field-shift
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --create-home fieldshift \
    && mkdir -p /var/lib/field-shift && chown fieldshift /var/lib/field-shift
COPY backend/app ./backend/app
COPY backend/tools ./backend/tools
COPY frontend ./frontend
COPY data/catalogs ./data/catalogs
COPY data/fixtures ./data/fixtures
COPY docs/validation/results/holdout-evaluation-v1.json ./docs/validation/results/holdout-evaluation-v1.json
COPY docs/validation/results/fresno-cimis-comparison.json ./docs/validation/results/fresno-cimis-comparison.json
WORKDIR /srv/field-shift/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FIELD_SHIFT_WARMUP=0 FIELD_SHIFT_DB=/var/lib/field-shift/field_shift.db FIELD_SHIFT_LAYER_DIR=/var/lib/field-shift/layers
USER fieldshift
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v2/health', timeout=4)"
# In-process jobs/SQLite are single-instance. Do not add workers without a durable queue.
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
