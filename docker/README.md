# Visionatrix in Docker

You can build and run Visionatrix in Docker container with GPU device passed trough.

## Build docker image

```bash
docker build . -t visionatrix/visionatrix
```

## Run Visionatrix docker container

```bash
docker run --name visionatrix --gpus all --rm --net host -d visionatrix/visionatrix
```

## Mount volumes with installed flows and models from the host

Mount `vix_flows` and `vix_models` folders with already downloaded and installed flows into
the container so that you don't have to download them again inside docker container.

```bash
docker run --name visionatrix --gpus all --rm --net host --volume ./docker/data/flows:/app/vix_flows \
	--volume ./docker/data/models:/apps/vix_models
```

## Mount tasks files outputs and database

If you want to keep the results on your host system and restore them between Docker container updates,
then you can additionally mount host directory into `/app/vix_tasks_files`:

```bash
docker run --name visionatrix --gpus all --rm --net host -v ./docker/data/flows:/app/vix_flows -v ./docker/data/models:/app/vix_models -v ./docker/data/tasks_files:/app/vix_tasks_files -d visionatrix/visionatrix
```
