FROM python:3.10-slim

ENV VIX_HOST "127.0.0.1"
ENV VIX_PORT 8288
ARG COMPUTE_DEVICE="CUDA"

WORKDIR /app

RUN apt-get update && apt-get install -y git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6

RUN python3 -m venv venv && venv/bin/python -m pip install -U pip && rm -rf ~/.cache/pip

RUN if [ "$COMPUTE_DEVICE" = "CUDA" ]; then \
	venv/bin/python -m pip install -U torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121 \
	&& rm -rf ~/.cache/pip; \
elif [ "$COMPUTE_DEVICE" = "ROCM" ]; then \
	venv/bin/python -m pip install -U --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/rocm6.0 \
	&& rm -rf ~/.cache/pip; \
elif [ "$COMPUTE_DEVICE" = "CPU" ]; then \
	venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
	&& rm -rf ~/.cache/pip; \
fi

RUN git clone --depth 1 https://github.com/Visionatrix/Visionatrix.git

RUN venv/bin/python -m pip install ./Visionatrix \
	&& venv/bin/python -m visionatrix install \
	&& rm -rf ~/.cache/pip

COPY ./entrypoint.sh /entrypoint.sh
COPY ./healthcheck.sh /healthcheck.sh
RUN chmod +x /entrypoint.sh && \
	chmod +x /healthcheck.sh

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD /healthcheck.sh
ENTRYPOINT ["/entrypoint.sh"]
