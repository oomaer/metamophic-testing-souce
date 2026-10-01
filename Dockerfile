# Node is needed by the HTTP servers; no npm packages are required.
FROM node:22-bookworm-slim AS node
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential ca-certificates cmake git libreadline-dev lsof procps \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
COPY requirements.txt ./
# Keep native compilation within modest memory limits.
RUN CMAKE_BUILD_PARALLEL_LEVEL=2 python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check

COPY . .
RUN python -c "from fandango.evolution.algorithm import SimpleGeneticAlgorithm; from fandango.language.parse.parse import parse; from pyftpdlib.handlers import FTPHandler; from twisted.mail import imap4; from aiosmtpd.controller import Controller; from dnslib.server import DNSServer" \
    && node --version

STOPSIGNAL SIGINT
ENTRYPOINT ["python", "/app/docker/run_experiments.py"]
