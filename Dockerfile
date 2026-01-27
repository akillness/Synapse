FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

FROM base AS runtime

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN useradd -m -u 1000 synaps && chown -R synaps:synaps /app
USER synaps

EXPOSE 5011 5012 5013 8000

ENV PYTHONPATH=/app

CMD ["python", "run_grpc_services.py", "--service", "all"]
