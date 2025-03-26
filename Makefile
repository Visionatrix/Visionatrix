.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Welcome to Visionatrix development. Please use \`make <target>\` where <target> is one of"
	@echo "  run                run the installed Visionatrix"
	@echo "  openapi       		build openapi.json"
	@echo "  build-client       build frontend client"
	@echo " "

.PHONY: run
run:
	@if [ -x ./.venv/bin/python ]; then \
		./.venv/bin/python -m visionatrix run --ui; \
	elif [ -x ./venv/bin/python ]; then \
		./venv/bin/python -m visionatrix run --ui; \
	else \
		echo "No virtual environment found."; \
		exit 1; \
	fi

.PHONY: push-cpu
push-cpu:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:release-cpu --build-arg BUILD_TYPE=cpu -f docker/Dockerfile .

.PHONY: push-latest-cpu
push-latest-cpu:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:latest-cpu --build-arg BUILD_TYPE=cpu -f docker/Dockerfile .

.PHONY: push-cuda
push-cuda:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:release-cuda --build-arg BUILD_TYPE=cuda -f docker/Dockerfile .

.PHONY: push-latest-cuda
push-latest-cuda:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:latest-cuda --build-arg BUILD_TYPE=cuda -f docker/Dockerfile .

.PHONY: push-rocm
push-rocm:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:release-rocm --build-arg BUILD_TYPE=rocm -f docker/Dockerfile .

.PHONY: push-latest-rocm
push-latest-rocm:
	docker login ghcr.io
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 --tag ghcr.io/visionatrix/visionatrix:latest-rocm --build-arg BUILD_TYPE=rocm -f docker/Dockerfile .

.PHONY: openapi
openapi:
	@echo "Building OpenAPI.json.."
	@python3 -m pip install . && python3 -m visionatrix --verbose=WARNING openapi

.PHONY: build-client
build-client:
	@echo "Building client..."
	@rm -rf visionatrix/client
	@cd web && npm run build && cp -r .output/public ../visionatrix/client

.PHONY: build-client-nextcloud
build-client-nextcloud:
	@echo "Building client for Nextcloud..."
	@rm -rf visionatrix/client && rm -rf web/.output/public/
	@cd web && NUXT_APP_BASE_URL=/index.php/apps/app_api/proxy/visionatrix/ NEXTCLOUD_INTEGRATION=true npm run build && \
		cp -r .output/public ../visionatrix/client
