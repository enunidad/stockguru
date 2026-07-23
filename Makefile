SVC ?=
CMD ?=

.PHONY: service run stop

service:
	@if "$(SVC)"=="" (echo SVC is required && exit /b 1)
	@if "$(CMD)"=="" (echo CMD is required && exit /b 1)
	$(MAKE) -C services/$(SVC) $(CMD)
	$(MAKE) -C services/$(SVC) clean

run:
	powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-Command','make service SVC=downloader CMD=run'"
	powershell -NoProfile -Command "Start-Sleep 2; Start-Process powershell -ArgumentList '-Command','make service SVC=analyzer CMD=run'"
	powershell -NoProfile -Command "Start-Sleep 4; Start-Process powershell -ArgumentList '-Command','make service SVC=frontend CMD=run'"
	powershell -NoProfile -Command "Start-Sleep 6; Start-Process 'http://localhost:8000/'"

stop:
	powershell -NoProfile -Command "$$ports = 8000,8080,8090; foreach ($$port in $$ports) { $$conns = Get-NetTCPConnection -LocalPort $$port -State Listen -ErrorAction SilentlyContinue; foreach ($$conn in $$conns) { if ($$conn.OwningProcess -gt 0) { Stop-Process -Id $$conn.OwningProcess -Force -ErrorAction SilentlyContinue } } }"