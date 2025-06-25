FROM python:3.12-slim

ENV VIX_HOST="127.0.0.1" \
    VIX_PORT=8288 \
    DATABASE_URI="sqlite+aiosqlite:////data/visionatrix.db" \
    BASE_DATA_DIR="/data"

ARG BUILD_TYPE
ARG CUDA_VERSION="128"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget curl git \
      python3-dev python3-setuptools netcat-traditional \
      libxml2-dev libxslt1-dev zlib1g-dev g++ \
      ffmpeg libsm6 libxext6 lshw procps libpq-dev libpq5 && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv venv && \
    set -eux; \
    if [ "$BUILD_TYPE" = "cuda" ]; then \
      venv/bin/python -m pip install torch torchaudio torchvision --extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION}; \
    elif [ "$BUILD_TYPE" = "rocm" ]; then \
      venv/bin/python -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/rocm6.3; \
    elif [ "$BUILD_TYPE" = "cpu" ]; then \
      venv/bin/python -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
      echo "Unsupported BUILD_TYPE: $BUILD_TYPE" && exit 1; \
    fi

COPY LICENSE.txt README.md pyproject.toml /app/
COPY visionatrix /app/visionatrix

COPY ./docker/entrypoint.py /entrypoint.py
COPY ./docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.py /healthcheck.sh

RUN --mount=type=cache,target=/root/.cache/pip \
    venv/bin/python -m pip install -U pip && \
    venv/bin/python -m pip install ".[pgsql]" && \
    mkdir tmp && \
    DATABASE_URI="sqlite+aiosqlite:///./tmp/visionatrix.db" BASE_DATA_DIR="./tmp" venv/bin/python -m visionatrix install && \
    rm -rf tmp visionatrix

HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=18 CMD /healthcheck.sh
ENTRYPOINT ["/app/venv/bin/python", "/entrypoint.py"]
