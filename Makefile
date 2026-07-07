SERVICE ?=
CMD ?=

.PHONY: service

service:
	@if "$(SERVICE)"=="" (echo SERVICE is required && exit /b 1)
	@if "$(CMD)"=="" (echo CMD is required && exit /b 1)
	$(MAKE) -C services/$(SERVICE) $(CMD)
	$(MAKE) -C services/$(SERVICE) clean