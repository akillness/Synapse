FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache \
    grpcio>=1.60.0 \
    grpcio-tools>=1.60.0 \
    grpcio-health-checking>=1.60.0 \
    protobuf>=4.25.0 \
    fastapi>=0.109.0 \
    "uvicorn[standard]>=0.27.0" \
    pydantic>=2.5.0 \
    httpx>=0.26.0 \
    textual>=0.47.0 \
    rich>=13.7.0

FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN useradd -m -u 1000 synaps && chown -R synaps:synaps /app
USER synaps

EXPOSE 5011 5012 5013 8000

ENV PYTHONPATH=/app

CMD ["python", "run_grpc_services.py", "--service", "all"]
