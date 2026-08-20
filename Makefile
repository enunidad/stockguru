SVC ?=
CMD ?=
PORT ?= 8000
MSG ?= dev update

SERVICE_DIRS := $(wildcard services/*/)
SERVICES := $(patsubst services/%/,%,$(SERVICE_DIRS))
PID_DIR := .pids

SELECTED_SERVICES := $(filter $(SERVICES),$(MAKECMDGOALS))


.PHONY: service test run-all-tests start-detached stop start-all stop-all run-local push-to-remote $(SERVICES)


# Service names are valid make targets, but don't do anything themselves.
$(SERVICES):
	@:


service:
	@if "$(SVC)"=="" (echo SVC is required && exit /b 1)
	@if "$(CMD)"=="" (echo CMD is required && exit /b 1)
	$(MAKE) -C services/$(SVC) $(CMD)


test:
	@if "$(SELECTED_SERVICES)"=="" (echo Usage: make ^<service...^> test && exit /b 1)
	@for %%s in ($(SELECTED_SERVICES)) do @$(MAKE) service SVC=%%s CMD=test || exit /b 1
	@for %%s in ($(SELECTED_SERVICES)) do @$(MAKE) service SVC=%%s CMD=clean


test-all:
	@echo ========================================
	@echo Running all service tests...
	@echo ========================================
	@for %%s in ($(SERVICES)) do @$(MAKE) service SVC=%%s CMD=test || exit /b 1
	@echo.
	@echo ========================================
	@echo All tests passed.
	@echo ========================================


start-detached:
	@if "$(SELECTED_SERVICES)"=="" (echo Usage: make ^<service...^> start-detached && exit /b 1)
	@if not exist "$(PID_DIR)" mkdir "$(PID_DIR)"
	@for %%s in ($(SELECTED_SERVICES)) do @powershell -NoProfile -Command "$$p = Start-Process powershell -PassThru -ArgumentList '-NoProfile','-Command','$(MAKE) service SVC=%%s CMD=run'; $$p.Id | Out-File -Encoding ascii '$(PID_DIR)/%%s.pid'; Write-Host 'Started %%s PID' $$p.Id"
	powershell -NoProfile -Command "Start-Sleep -Seconds 2"


stop:
	@if "$(SELECTED_SERVICES)"=="" (echo Usage: make ^<service...^> stop && exit /b 1)
	@for %%s in ($(SELECTED_SERVICES)) do @powershell -NoProfile -Command "if (Test-Path '$(PID_DIR)/%%s.pid') { $$processId = Get-Content '$(PID_DIR)/%%s.pid'; Write-Host 'Stopping %%s PID' $$processId; taskkill /PID $$processId /T /F | Out-Null; Remove-Item '$(PID_DIR)/%%s.pid' -Force } else { Write-Host '%%s is not running.' }"


start-all:
	@$(MAKE) $(SERVICES) start-detached


stop-all:
	@$(MAKE) $(SERVICES) stop


run-local: start-all
	powershell -NoProfile -Command "Start-Process 'http://localhost:$(PORT)/'"


push-to-remote:
	$(MAKE) service SVC=downloader CMD=clean-cache
	git add .
	git commit -m '$(MSG)'
	git push