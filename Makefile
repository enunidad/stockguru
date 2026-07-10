SVC ?=
CMD ?=

.PHONY: service

service:
	@if "$(SVC)"=="" (echo SVC is required && exit /b 1)
	@if "$(CMD)"=="" (echo CMD is required && exit /b 1)
	$(MAKE) -C services/$(SVC) $(CMD)
	$(MAKE) -C services/$(SVC) clean