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
	@rm -rf client
	@cd web && npm run build && cp -r .output/public ../client
