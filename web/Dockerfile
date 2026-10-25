# MemLedger console: docker build -f web/Dockerfile -t memledger-console .
#   docker run -p 8000:8000 -v memledger:/data -v $PWD/users.json:/run/users.json:ro \
#     -e MEMLEDGER_USERS=/run/users.json memledger-console
FROM node:22-alpine AS ui
WORKDIR /ui
COPY web/ui/package.json web/ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ui/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY memledger/ memledger/
RUN pip install --no-cache-dir -e ".[web]"
COPY eval/ eval/
COPY infra/ infra/
COPY demo/ demo/
COPY web/ web/
COPY --from=ui /ui/dist web/ui/dist
RUN useradd -r -u 10001 memledger && mkdir /data && chown memledger /data
USER memledger
ENV PYTHONPATH=/app MEMLEDGER_DATA_DIR=/data MEMLEDGER_GUARD_BACKEND=lexical PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "-m", "web", "--host", "0.0.0.0"]
