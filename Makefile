SVC ?=
CMD ?=
PORT ?= 8000
MSG ?= dev update

SERVICES := $(patsubst services/%/Makefile,%,$(wildcard services/*/Makefile))
PID_DIR := .pids

SELECTED_SERVICES := $(filter $(SERVICES),$(MAKECMDGOALS))

PYTHON ?= python3
export PYTHON
# Keep the detached launcher from running during make --dry-run.
BACKGROUND_MAKE = $(MAKE)


.PHONY: service install run test test-all integration-test full-test start-detached stop \
        start-all stop-all run-local clean clean-all push-to-remote $(SERVICES)


# Service names are valid make targets, but don't do anything themselves.
$(SERVICES):
	@:

service:
	@if [ -z "$(SVC)" ]; then echo "SVC is required" >&2; exit 1; fi
	@if [ -z "$(CMD)" ]; then echo "CMD is required" >&2; exit 1; fi
	@$(MAKE) -C services/$(SVC) $(CMD)

install:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> install" >&2; exit 1; fi
	@for svc in $(SELECTED_SERVICES); do $(MAKE) service SVC="$$svc" CMD=install || exit $$?; done

run:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> run" >&2; exit 1; fi
	@for svc in $(SELECTED_SERVICES); do $(MAKE) service SVC="$$svc" CMD=run || exit $$?; done

test:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> test" >&2; exit 1; fi
	@for svc in $(SELECTED_SERVICES); do \
		docker compose run --build --rm --no-deps -T "$$svc" python -m pytest tests -v || exit $$?; \
	done


test-all:
	@echo ========================================
	@echo Running all service tests...
	@echo ========================================
	@$(MAKE) $(SERVICES) test
	@echo
	@echo ========================================
	@echo All unit tests passed.
	@echo ========================================

integration-test:
	@echo ========================================
	@echo Running all public endpoints tests...
	@echo ========================================
	@set -e; \
	compose="docker compose -f docker-compose.yml -f docker-compose.integration.yml -p stockguru-integration-$$$$"; \
	trap '$$compose down --volumes --rmi local' EXIT; \
	$$compose up --build --wait; \
	$$compose run --rm --no-deps -T \
		--volume "$(CURDIR)/integration_tests:/app/integration_tests:ro" \
		-e FRONTEND_BASE_URL=http://frontend:8000 \
		frontend python -m pytest integration_tests -v
	@echo ========================================
	@echo All endpoints passed.
	@echo ========================================


full-test: test-all
	$(MAKE) integration-test
	@echo ========================================
	@echo Ready to merge.
	@echo ========================================

start-detached:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> start-detached" >&2; exit 1; fi
	@mkdir -p "$(PID_DIR)"
	@set -e; for svc in $(SELECTED_SERVICES); do \
		pid_file="$(PID_DIR)/$$svc.pid"; \
		if [ -s "$$pid_file" ] && /bin/kill -0 -- "-$$(cat "$$pid_file")" 2>/dev/null; then \
			echo "$$svc is already running."; \
			continue; \
		fi; \
		nohup setsid $(BACKGROUND_MAKE) service SVC="$$svc" CMD=run </dev/null >"$(PID_DIR)/$$svc.log" 2>&1 & \
		pid=$$!; \
		echo "$$pid" >"$$pid_file"; \
		echo "Started $$svc (PID $$pid). Log: $(PID_DIR)/$$svc.log"; \
	done
	@sleep 2

stop:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> stop" >&2; exit 1; fi
	@set -e; for svc in $(SELECTED_SERVICES); do \
		pid_file="$(PID_DIR)/$$svc.pid"; \
		if [ -s "$$pid_file" ]; then \
			pid=$$(cat "$$pid_file"); \
			if /bin/kill -0 -- "-$$pid" 2>/dev/null; then \
				echo "Stopping $$svc (PID $$pid)."; \
				/bin/kill -TERM -- "-$$pid"; \
			else \
				echo "$$svc is not running."; \
			fi; \
			rm -f "$$pid_file"; \
		else \
			echo "$$svc is not running."; \
		fi; \
	done


start-all:
	@$(MAKE) $(SERVICES) start-detached


stop-all:
	@$(MAKE) $(SERVICES) stop


run-local: start-all
	xdg-open "http://localhost:$(PORT)/"

clean:
	@if [ -z "$(SELECTED_SERVICES)" ]; then echo "Usage: make <service...> clean" >&2; exit 1; fi
	@for svc in $(SELECTED_SERVICES); do $(MAKE) service SVC="$$svc" CMD=clean || exit $$?; done

clean-all:
	$(MAKE) $(SERVICES) clean

push-to-remote:
	$(MAKE) clean-all
	git add .
	git commit -m '$(MSG)'
	git push
