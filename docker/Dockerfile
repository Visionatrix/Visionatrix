FROM python:3.10-slim

ENV COMFY_DEBUG 0
ENV VIX_HOST "127.0.0.1"
ENV VIX_PORT 8288

WORKDIR /app

RUN apt-get update && apt-get install -y git \
	python3-dev python3-setuptools netcat-traditional \
	libxml2-dev libxslt1-dev zlib1g-dev g++ \
	ffmpeg libsm6 libxext6

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

RUN git clone --depth 1 https://github.com/Visionatrix/Visionatrix.git .

RUN python3 -m venv venv

RUN . venv/bin/activate && python3 -m pip install -U pip \
	&& python3 -m pip install .[app] \
	&& python3 -m visionatrix install \
	&& rm -rf ~/.cache/pip

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD /healthcheck.sh
ENTRYPOINT ["/entrypoint.sh"]
