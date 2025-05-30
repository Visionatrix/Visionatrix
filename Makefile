.DEFAULT_GOAL := help

VISIONATRIX_VERSION := $(shell sed -n "s/^__version__ = ['\"]\([^'\"]*\)['\"]/\1/p" visionatrix/_version.py)

ifeq ($(VISIONATRIX_VERSION),)
$(error Could not extract version from visionatrix/_version.py. Please check the file.)
endif

IS_DEV_VERSION := $(findstring .dev,$(VISIONATRIX_VERSION))

CPU_TAG_OPTIONS := --tag ghcr.io/visionatrix/visionatrix:$(VISIONATRIX_VERSION)-cpu
CUDA_TAG_OPTIONS := --tag ghcr.io/visionatrix/visionatrix:$(VISIONATRIX_VERSION)-cuda
ROCM_TAG_OPTIONS := --tag ghcr.io/visionatrix/visionatrix:$(VISIONATRIX_VERSION)-rocm
ifeq ($(IS_DEV_VERSION),)
    CPU_TAG_OPTIONS  += --tag ghcr.io/visionatrix/visionatrix:release-cpu
    CUDA_TAG_OPTIONS += --tag ghcr.io/visionatrix/visionatrix:release-cuda
    ROCM_TAG_OPTIONS += --tag ghcr.io/visionatrix/visionatrix:release-rocm
    VERSION_TYPE_MSG := This is a RELEASE version ($(VISIONATRIX_VERSION)). Tagging also as 'release-<type>'.
else
    CPU_TAG_OPTIONS  += --tag ghcr.io/visionatrix/visionatrix:latest-cpu
    CUDA_TAG_OPTIONS += --tag ghcr.io/visionatrix/visionatrix:latest-cuda
    ROCM_TAG_OPTIONS += --tag ghcr.io/visionatrix/visionatrix:latest-rocm
    VERSION_TYPE_MSG := This is a DEV version ($(VISIONATRIX_VERSION)). Tagging also as 'latest-<type>'.
endif


.PHONY: help
help:
	@echo "Welcome to Visionatrix development. Please use \`make <target>\` where <target> is one of"
	@echo "  run                run the installed Visionatrix"
	@echo "  openapi       		build openapi.json"
	@echo "  build-client       build frontend client"
	@echo "  push-cpu           build and push CPU image."
	@echo "                     Tags: $(VISIONATRIX_VERSION)-cpu. Also 'release-cpu' for releases, or 'latest-cpu' for .dev versions."
	@echo "  push-cuda          build and push CUDA image."
	@echo "                     Tags: $(VISIONATRIX_VERSION)-cuda. Also 'release-cuda' for releases, or 'latest-cuda' for .dev versions."
	@echo "  push-rocm          build and push ROCm image."
	@echo "                     Tags: $(VISIONATRIX_VERSION)-rocm. Also 'release-rocm' for releases, or 'latest-rocm' for .dev versions."
	@echo " "
	@echo "Current Visionatrix Version: $(VISIONATRIX_VERSION)"
	@echo "$(VERSION_TYPE_MSG)"

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
	@echo "Building and pushing CPU image..."
	@echo "$(VERSION_TYPE_MSG)"
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 \
		$(CPU_TAG_OPTIONS) \
		--build-arg BUILD_TYPE=cpu -f docker/Dockerfile .

.PHONY: push-cuda
push-cuda:
	@echo "Building and pushing CUDA image..."
	@echo "$(VERSION_TYPE_MSG)"
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 \
		$(CUDA_TAG_OPTIONS) \
		--build-arg BUILD_TYPE=cuda -f docker/Dockerfile .

.PHONY: push-rocm
push-rocm:
	@echo "Building and pushing ROCm image..."
	@echo "$(VERSION_TYPE_MSG)"
	DOCKER_BUILDKIT=1 docker buildx build --progress=plain --push --platform linux/amd64 \
		$(ROCM_TAG_OPTIONS) \
		--build-arg BUILD_TYPE=rocm -f docker/Dockerfile .

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
	@rm -rf web/.output/public/
	@cd web && NUXT_APP_BASE_URL=/exapps/visionatrix/ NEXTCLOUD_INTEGRATION=true npm run build && \
		cp -r .output/public ../visionatrix/client_harp
