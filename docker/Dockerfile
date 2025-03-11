FROM python:3.12-slim

ENV VIX_HOST="127.0.0.1"
ENV VIX_PORT=8288
ENV DATABASE_URI="sqlite+aiosqlite:////data/visionatrix.db"
ENV BASE_DATA_DIR="/data"
ARG BUILD_TYPE

VOLUME ["/data"]
WORKDIR /app

RUN apt-get update && apt-get install -y wget curl git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6 lshw procps libpq-dev libpq5


RUN python3 -m venv venv \
    && venv/bin/python -m pip install -U pip \
    && set -eux; \
       if [ "$BUILD_TYPE" = "cuda" ]; then \
         venv/bin/python -m pip install torch torchaudio torchvision --extra-index-url https://download.pytorch.org/whl/cu126; \
       elif [ "$BUILD_TYPE" = "rocm" ]; then \
         venv/bin/python -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/rocm6.2.4; \
       elif [ "$BUILD_TYPE" = "cpu" ]; then \
         venv/bin/python -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cpu; \
       else \
         echo "Unsupported BUILD_TYPE: $BUILD_TYPE"; exit 1; \
       fi \
    && rm -rf ~/.cache/pip

COPY visionatrix /app/visionatrix
COPY LICENSE.txt README.md pyproject.toml /app/

COPY ./docker/entrypoint.sh /entrypoint.sh
COPY ./docker/healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh /healthcheck.sh

RUN venv/bin/python -m pip install ".[pgsql]" \
    && mkdir ./tmp \
	&& DATABASE_URI="sqlite+aiosqlite:///./tmp/visionatrix.db" BASE_DATA_DIR="./tmp" venv/bin/python -m visionatrix install \
    && rm -rf ./tmp visionatrix ~/.cache/pip

HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=18 CMD /healthcheck.sh
ENTRYPOINT ["/entrypoint.sh"]
