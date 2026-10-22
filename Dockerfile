FROM python:3.12-slim
WORKDIR /app
# Install the PostgreSQL adapter as well as the base API dependencies.
# SQLite remains supported for local/demo runs.
COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt
COPY server.py storage.py request_schema.py ./
COPY static ./static
RUN useradd -r -u 10001 scene && mkdir -p /data && chown scene:scene /data
USER scene
ENV SCENE_DB=/data/scene.db SCENE_DEMO=0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000","--workers","1"]
