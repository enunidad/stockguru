SVC ?=
CMD ?=
SVCS ?= downloader analyzer chartmgr frontend
PORT ?= 8000
MSG ?= dev update

.PHONY: service run stop

service:
	@if "$(SVC)"=="" (echo SVC is required && exit /b 1)
	@if "$(CMD)"=="" (echo CMD is required && exit /b 1)
	$(MAKE) -C services/$(SVC) $(CMD)
	$(MAKE) -C services/$(SVC) clean

test-service:
	$(MAKE) service SVC=$(SVC) CMD=test
	$(MAKE) service SVC=$(SVC) CMD=clean

run-all-tests:
	@echo ========================================
	@echo Running all service tests...
	@echo ========================================
	@for %%s in (downloader analyzer frontend) do @$(MAKE) test-service SVC=%%s || exit /b 1
	@echo.
	@echo ========================================
	@echo All tests passed.
	@echo ========================================

start-one-service:
	powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-Command','make service SVC=$(SVC) CMD=run'"
	powershell -NoProfile -Command "Start-Sleep -Seconds 2"

start-many-services:
	powershell -NoProfile -Command "foreach ($$svc in '$(SVCS)'.Split(' ')) { Write-Host \"Starting $$svc...\"; & make start-one-service SVC=$$svc }"

start-web-port:
	powershell -NoProfile -Command "Start-Process 'http://localhost:$(PORT)/'"

run:
	$(MAKE) start-many-services SVCS="$(SVCS)"
	$(MAKE) start-web-port PORT=$(PORT)

stop:
	powershell -NoProfile -Command "$$ports = 8000,8080,8090,8050; foreach ($$port in $$ports) { $$conns = Get-NetTCPConnection -LocalPort $$port -State Listen -ErrorAction SilentlyContinue; foreach ($$conn in $$conns) { if ($$conn.OwningProcess -gt 0) { Stop-Process -Id $$conn.OwningProcess -Force -ErrorAction SilentlyContinue } } }"

push-to-remote:
	git add .
	git commit -m '$(MSG)'
	git push