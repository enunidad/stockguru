.PHONY: downloader-smoke downloader-test

downloader-smoke:
	$(MAKE) -C services/downloader run
	$(MAKE) -C services/downloader clean

downloader-test:
	$(MAKE) -C services/downloader test
	$(MAKE) -C services/downloader clean