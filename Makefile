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
	@echo "  build-client       build frontend client"
	@echo " "

.PHONY: build-client
build-client:
	@echo "Building client..."
	@rm -rf visionatrix/client
	@cd web && npm run build && cp -r .output/public ../visionatrix/client

.PHONY: build-client-nextcloud
build-client-nextcloud:
	@echo "Building client for Nextcloud..."
	@rm -rf visionatrix/client
	@cd web && NUXT_APP_BUILD_ASSETS_DIR="/index.php/apps/app_api/proxy/vix/iframe/_nuxt/" \
		NUXT_APP_BASE_URL=/index.php/apps/app_api/proxy/vix/iframe/ npm run build && \
		cp -r .output/public ../visionatrix/client
	@cd web && \
		NUXT_APP_BUILD_ASSETS_DIR="/index.php/apps/app_api/proxy/vix/iframe/_nuxt/" && \
		mkdir -p ../visionatrix/client/_nuxt && \
		cp -r .output/public$${NUXT_APP_BUILD_ASSETS_DIR}* ../visionatrix/client/_nuxt/
