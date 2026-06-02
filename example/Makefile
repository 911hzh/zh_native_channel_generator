

# >>> zh_native_channel_generator
ZH_NATIVE_CHANNEL_GENERATOR ?= dart run zh_native_channel_generator:generate_native_channel
ZH_NATIVE_CHANNEL_CONFIG ?= zh_native_channel_config.json

.PHONY: clean-generated build-runner-sync-config build-runner-build create-platformcode-all create-platformcode-ios create-platformcode-android create-platformcode-web gen

clean-generated:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --clean-generated-only

build-runner-sync-config:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --sync-build-config-only

build-runner-build: build-runner-sync-config
	@if [ ! -f pubspec.yaml ]; then echo "当前目录没有 pubspec.yaml，跳过 build_runner。"; else dart run build_runner build; fi

gen:
	$(MAKE) clean-generated
	$(MAKE) build-runner-build
	$(MAKE) create-platformcode-all

create-platformcode-all:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform all

create-platformcode-ios:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform ios

create-platformcode-android:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform android

create-platformcode-web:
	$(ZH_NATIVE_CHANNEL_GENERATOR) $(ZH_NATIVE_CHANNEL_CONFIG) --platform web
# <<< zh_native_channel_generator



