# Visionatrix in Docker

You can build and run Visionatrix in Docker container with GPU device passed trough.

## Build docker image

> [!NOTE]
> By default image is being built with pytorch CUDA support for NVIDIA.
> You can change this to AMD using ENV variable `GPU_VENDOR="AMD"`

```bash
docker build . -t visionatrix/visionatrix
```

## Run Visionatrix docker container

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 -d visionatrix/visionatrix
```

## Mount volumes with installed flows and models from the host

Mount `vix_flows` and `vix_models` folders with already downloaded and installed flows into
the container so that you don't have to download them again inside docker container or after update.

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 \
	--volume ./docker/data/flows:/app/vix_flows --volume ./docker/data/models:/apps/vix_models
```

## Mount tasks files outputs and database

If you want to keep the results on your host system and restore them between Docker container updates,
then you can additionally mount host directory into `/app/vix_tasks_files`:

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 \
	-v ./docker/data/flows:/app/vix_flows -v ./docker/data/models:/app/vix_models \
	-v ./docker/data/tasks_files:/app/vix_tasks_files -d visionatrix/visionatrix
```

## Docker compose

The same container can be created using docker compose, there are two options available:

1. visionatrix_nvidia - client and server with NVIDIA gpus attached

```bash
docker compose up -d visionatrix_nvidia
```

2. visionatrix_amd - client and server with AMD gpus attached

```bash
docker compose up -d visionatrix_amd
```
