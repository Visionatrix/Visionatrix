.DEFAULT_GOAL := help

.PHONY: docs
.PHONY: html
docs html:
	rm -rf docs/_build
	$(MAKE) -C docs html

.PHONY: help
help:
	@echo "Welcome to Visionatrix development. Please use \`make <target>\` where <target> is one of"
	@echo "  docs               make HTML docs"
	@echo "  openapi       		build openapi.json"
	@echo "  build-client       build frontend client"
	@echo " "

.PHONY: openapi
openapi:
	@echo "Building OpenAPI.json.."
	@python3 scripts/generate_openapi.py

.PHONY: build-client
build-client:
	@echo "Building client..."
	@rm -rf visionatrix/client
	@cd web && npm run build && cp -r .output/public ../visionatrix/client

.PHONY: build-client-nextcloud
build-client-nextcloud:
	@echo "Building client for Nextcloud..."
	@rm -rf visionatrix/client
	@cd web && NUXT_APP_BASE_URL=/index.php/apps/app_api/proxy/vix/ npm run build && \
		cp -r .output/public ../visionatrix/client
