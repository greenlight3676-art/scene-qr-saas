FROM python:3.12-slim
WORKDIR /app
# Install the PostgreSQL adapter as well as the base API dependencies.
# SQLite remains supported for local/demo runs.
COPY requirements.txt requirements-postgres.txt ./
RUN pip install --no-cache-dir -r requirements-postgres.txt
COPY server.py storage.py request_schema.py security_schema.py managed_auth.py backend_schema.py auth_backend.py operations.py platform_api.py growth.py billing.py mail_delivery.py ./
COPY static ./static
# Public CA downloaded from the Supabase database settings certificate link.
COPY certs/supabase-prod-ca.crt /app/certs/supabase-prod-ca.crt
RUN useradd -r -u 10001 scene && mkdir -p /data && chown scene:scene /data
USER scene
ENV SCENE_DB=/data/scene.db SCENE_DEMO=0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log","--proxy-headers","--forwarded-allow-ips=127.0.0.1"]
