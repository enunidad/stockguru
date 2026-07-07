.PHONY: test test-downloader

test-downloader:
	$(MAKE) -C services/downloader run