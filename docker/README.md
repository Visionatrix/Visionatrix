# Visionatrix in Docker

You can build and run Visionatrix in Docker container with GPU device passthrough.

## Build docker image

> [!NOTE]
> By default image is being built with pytorch CUDA support for NVIDIA.

```bash
docker build . -t visionatrix/visionatrix_nvidia --build-arg="COMPUTE_DEVICE=CUDA"
```

### Build for AMD GPU

```bash
docker build . -t visionatrix/visionatrix_amd --build-arg="COMPUTE_DEVICE=ROCM"
```

## Build for CPU

```bash
docker build . -t visionatrix/visionatrix_cpu --build-arg="COMPUTE_DEVICE=CPU"
```

## Run Visionatrix docker container

For NVIDIA:

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 -d visionatrix/visionatrix_nvidia
```

For AMD:

```bash
docker run --name visionatrix --device /dev/dri --device /dev/kfd -p 8288:8288 -e VIX_HOST=0.0.0.0 -d visionatrix/visionatrix_amd
```

For CPU:

```bash
docker run --name visionatrix -p 8288:8288 -e VIX_HOST=0.0.0.0 -d visionatrix/visionatrix_cpu
```

## Mount volumes with installed flows and models from the host

Mount `vix_flows` and `vix_models` folders with already downloaded and installed flows into
the container so that you don't have to download them again inside docker container or after update.

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 \
	--volume ./docker/data/flows:/app/vix_flows --volume ./docker/data/models:/apps/vix_models \
	-d visionatrix/visionatrix_<compute_device>
```

## Mount tasks files outputs and database

If you want to keep the results on your host system and restore them between Docker container updates,
then you can additionally mount host directory into `/app/vix_tasks_files`:

```bash
docker run --name visionatrix --gpus all -p 8288:8288 -e VIX_HOST=0.0.0.0 \
	-v ./docker/data/flows:/app/vix_flows -v ./docker/data/models:/app/vix_models \
	-v ./docker/data/tasks_files:/app/vix_tasks_files -d visionatrix/visionatrix_<compute_device>
```

## Docker compose

The same container can be created using docker compose:

1. `visionatrix_nvidia` - client and server with NVIDIA gpus attached

    ```bash
    docker compose up -d visionatrix_nvidia
    ```

2. `visionatrix_amd` - client and server with AMD gpus attached

    ```bash
    docker compose up -d visionatrix_amd
    ```

3. `visionatrix_cpu` - client and server on CPU without GPUs

    ```bash
    docker compose up -d visionatrix_cpu
    ```
