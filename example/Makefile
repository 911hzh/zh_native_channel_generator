

# >>> zh_native_channel_generator
PYTHON ?= python3
ZH_NATIVE_CHANNEL_GENERATOR ?= ../scripts/generate_native_channel.py
ZH_NATIVE_CHANNEL_CONFIG ?= zh_native_channel_config.json

.PHONY: build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web gen

build-runner-sync-config:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

build-runner-build: build-runner-sync-config
	@if [ ! -f pubspec.yaml ]; then echo "当前目录没有 pubspec.yaml，跳过 build_runner。"; else dart run build_runner build; fi

gen:
	$(MAKE) build-runner-build
	$(MAKE) create-platformcode-all

create-platformcode-all:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

create-platformcode-ios:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

create-platformcode-android:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

create-platformcode-web:
	$(PYTHON) $(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
# <<< zh_native_channel_generator






















