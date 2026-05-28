# >>> zh_native_channel_generator
PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= scripts/generate_native_channel.py
ZH_NATIVE_CHANNEL_CONFIG ?= zh_native_channel_config.json

.PHONY: build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web

build-runner-sync-config:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

build-runner-build: build-runner-sync-config
	flutter pub run build_runner build --delete-conflicting-outputs

create-platformcode-all:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

create-platformcode-ios:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

create-platformcode-android:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

create-platformcode-web:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
# <<< zh_native_channel_generator
