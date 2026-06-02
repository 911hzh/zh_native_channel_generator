EXAMPLE_DIR ?= example

.PHONY: clean-generated build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web gen

clean-generated:
	$(MAKE) -C $(EXAMPLE_DIR) clean-generated

build-runner-sync-config:
	$(MAKE) -C $(EXAMPLE_DIR) build-runner-sync-config

build-runner-build:
	$(MAKE) -C $(EXAMPLE_DIR) build-runner-build

gen:
	$(MAKE) -C $(EXAMPLE_DIR) gen

create-platformcode-all:
	$(MAKE) -C $(EXAMPLE_DIR) create-platformcode-all

create-platformcode-ios:
	$(MAKE) -C $(EXAMPLE_DIR) create-platformcode-ios

create-platformcode-android:
	$(MAKE) -C $(EXAMPLE_DIR) create-platformcode-android

create-platformcode-web:
	$(MAKE) -C $(EXAMPLE_DIR) create-platformcode-web
