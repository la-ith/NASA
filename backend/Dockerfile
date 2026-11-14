# Build from repository root: docker build -f backend/Dockerfile -t field-shift-backend .
FROM python:3.12-slim
WORKDIR /srv/field-shift
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd --create-home fieldshift \
    && mkdir -p /var/lib/field-shift && chown fieldshift /var/lib/field-shift
COPY backend/app ./backend/app
COPY data/catalogs ./data/catalogs
COPY data/fixtures ./data/fixtures
WORKDIR /srv/field-shift/backend
ENV FIELD_SHIFT_WARMUP=0 FIELD_SHIFT_DB=/var/lib/field-shift/field_shift.db
USER fieldshift
EXPOSE 8000
# In-process jobs/SQLite are single-instance. Do not add workers without a durable queue.
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
