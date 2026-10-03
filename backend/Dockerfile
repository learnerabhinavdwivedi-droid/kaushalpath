# KaushalPath backend image — python slim, non-root (PHASE_0 task 5)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Non-root user (RULES: least privilege)
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# Prod entrypoint + a writable, app-owned mount point for the SQLite volume.
# The image keeps `uvicorn` as the default CMD (dev compose relies on it); the
# prod compose opts into the entrypoint script explicitly.
RUN chmod +x /app/entrypoint.prod.sh \
    && mkdir -p /data \
    && chown app:app /data

# Only app source needs to be readable/writable by the runtime user
RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
