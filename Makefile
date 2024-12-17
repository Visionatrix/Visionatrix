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
	@cd web && NUXT_APP_BASE_URL=/index.php/apps/app_api/proxy/visionatrix/ npm run build && \
		cp -r .output/public ../visionatrix/client
