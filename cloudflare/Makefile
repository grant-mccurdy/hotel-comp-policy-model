.PHONY: sync ui-check dev

UV ?= uv

sync:
	$(UV) sync

ui-check:
	python3 ../scripts/build_worker_ui.py --check

dev: ui-check
	$(UV) run pywrangler dev
