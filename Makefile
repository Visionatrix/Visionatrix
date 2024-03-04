.DEFAULT_GOAL := help

.PHONY: docs
.PHONY: html
docs html:
	rm -rf docs/_build
	$(MAKE) -C docs html

.PHONY: help
help:
	@echo "Welcome to AI-Media-Wizard development. Please use \`make <target>\` where <target> is one of"
	@echo "  docs               make HTML docs"
	@echo " "
